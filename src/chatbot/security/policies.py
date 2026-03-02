"""Chatbot security policies.

Defines a small interface for subschema-specific security and a simple
registry/lookup mechanism. The goal is to keep the core chatbot flow
clean while allowing each subschema to plug in its own security rules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import import_module
from typing import Dict, Optional, Tuple, Any

from src.core.registry import scheme_registry


@dataclass
class SubschemeSecurityPolicy:
    """Base interface for subschema-specific chatbot security."""

    def enforce_question(
        self, question: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Validate or adjust the natural-language question.

        Returns (allowed, result). If allowed is False, result should be a
        short, user-facing explanation. If allowed is True, result is the
        (possibly modified) question.
        """
        return True, question

    def enforce_sql(
        self, sql: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Validate or adjust the generated SQL before execution.

        Returns (allowed, result). If allowed is False, result should be a
        short, user-facing explanation. If allowed is True, result is the
        (possibly modified) SQL to execute.
        """
        return True, sql


class DivisionDistrictSecurityMixin:
    """
    Shared helper for division-level and district-scoped security rules.

    This is intentionally generic and stateless so that individual
    subschema policies can compose it without duplicating logic.
    """

    _ELEVATED_ROLES = {"dco", "admin"}

    def _enforce_division_question(
        self, question: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Block division-level queries from non-elevated district users.
        """
        if user_context is None:
            return True, question

        role = (user_context.get("role") or "").lower()
        level = (user_context.get("level") or "").lower()

        q_lower = question.lower()
        is_division_query = any(
            token in q_lower
            for token in ["konkan division", "mumbai division", "division"]
        )

        if is_division_query and level == "district" and role not in self._ELEVATED_ROLES:
            return (
                False,
                "Division-level summaries are restricted to DCO and admin users.",
            )

        return True, question

    def _enforce_district_sql_scope(
        self, sql: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Restrict district-level users to their own district when the SQL
        explicitly filters by \"district\".
        """
        if user_context is None:
            return True, sql

        role = (user_context.get("role") or "").lower()
        level = (user_context.get("level") or "").lower()
        unit = (user_context.get("unit") or "").lower()

        # Only enforce district scoping for district-level users that are
        # not elevated and have a concrete unit.
        if level != "district" or not unit or role in self._ELEVATED_ROLES:
            return True, sql

        sql_lower = sql.lower()

        # If the query filters by district but does not include the
        # user's own district, block it to prevent cross-district access.
        if '"district"' in sql_lower and unit not in sql_lower:
            return (
                False,
                "You are only allowed to query data for your own district.",
            )

        return True, sql


class _GenericSecurityPolicy(SubschemeSecurityPolicy):
    """
    Conservative, generic policy applied when no subschema-specific
    policy is available.
    """

    def enforce_question(
        self, question: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        # Allow internal/health-check style calls without user context.
        if user_context is None:
            return True, question

        username = (user_context.get("username") or "").strip()
        role = (user_context.get("role") or "").strip()
        if not username or not role:
            return False, "Your session is missing required authentication information."

        return True, question

    def enforce_sql(
        self, sql: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        # Allow internal calls without user context.
        if user_context is None:
            return True, sql

        sub_scheme_code = (user_context.get("sub_scheme_code") or "").strip()
        if not sub_scheme_code:
            return False, "A sub-scheme must be selected to use the assistant."

        # Validate that query is scoped to the correct subscheme tables
        # by checking table names against the scheme config
        config = scheme_registry.get_scheme(sub_scheme_code)
        if not config:
            return False, "Selected sub-scheme is not configured for chatbot access."

        # Extract expected table names from config forms
        expected_tables = set()
        if config.forms:
            for form_name, form_config in config.forms.items():
                if hasattr(form_config, 'table_name') and form_config.table_name:
                    expected_tables.add(form_config.table_name)

        sql_lower = sql.lower()

        # If expected tables are defined, validate that query only references
        # tables from this subscheme (scheme-agnostic validation)
        if expected_tables:
            # Check if at least one expected table is referenced in the SQL
            # This validates scope without hardcoding table name patterns
            if not any(table.lower() in sql_lower for table in expected_tables):
                return (
                    False,
                    "Query is attempting to access data outside the selected sub-scheme.",
                )

        return True, sql


_GENERIC_POLICY = _GenericSecurityPolicy()
_POLICY_CACHE: Dict[str, SubschemeSecurityPolicy] = {}


def get_policy_for_subscheme(
    sub_scheme_code: Optional[str],
) -> SubschemeSecurityPolicy:
    """
    Resolve the security policy for a given sub-scheme.

    Uses lazy imports so that subschema-specific policies live alongside
    their prompt configs without bloating the core chatbot module.
    """
    if not sub_scheme_code:
        return _GENERIC_POLICY

    code = sub_scheme_code.strip()
    if not code:
        return _GENERIC_POLICY

    if code in _POLICY_CACHE:
        return _POLICY_CACHE[code]

    # Load from new schemas structure
    scheme_code = code[:4] if len(code) >= 4 else None
    
    if scheme_code:
        try:
            module = import_module(f"src.chatbot.schemas.s{scheme_code}.subs.{code}.security_policy")
            policy = getattr(module, "POLICY", None)
            if isinstance(policy, SubschemeSecurityPolicy):
                _POLICY_CACHE[code] = policy
                return policy
        except ImportError:
            pass
        except Exception:
            pass

    return _GENERIC_POLICY


