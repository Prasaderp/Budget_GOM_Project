"""Security policy for subschema 20750249."""
from __future__ import annotations

from typing import Dict, Optional, Tuple, Any

from src.chatbot.security import SubschemeSecurityPolicy


class _Policy20750249(SubschemeSecurityPolicy):
    """
    Subschema-specific security rules for 20750249.

    - DCO-level, sub-head expenditure only (no districts/classes/categories).
    - Enforces read-only (SELECT-only) SQL.
    - Prevents cross-subschema access to other sub_head_expenditure tables.
    """

    _ALLOWED_LEVEL = "dco"
    _TABLE_NAME = "sub_head_expenditure_20750249"

    def _is_dco_user(self, user_context: Optional[Dict[str, Any]]) -> bool:
        if not user_context:
            return False
        level = (user_context.get("level") or "").strip().lower()
        return level == self._ALLOWED_LEVEL

    def enforce_question(
        self, question: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Allow assistant access only for authenticated DCO-level users and
        for the correct subscheme binding.
        """
        if not user_context:
            return False, "Assistant access for this sub-scheme requires DCO-level authentication."

        if not self._is_dco_user(user_context):
            return False, "This sub-scheme is restricted to DCO-level users."

        sub_code = (user_context.get("sub_scheme_code") or "").strip()
        if sub_code != "20750249":
            return False, "Sub-scheme context mismatch. Please re-select the sub-scheme and try again."

        return True, question

    def enforce_sql(
        self, sql: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Enforce read-only, subscheme-scoped SQL for sub_head_expenditure_20750249.
        """
        if not self._is_dco_user(user_context):
            return False, "Only DCO-level users can execute assistant queries for this sub-scheme."

        sql_lower = (sql or "").lower()

        # Hard block any non-SELECT statement patterns.
        forbidden_tokens = [
            " insert ",
            " update ",
            " delete ",
            " alter ",
            " drop ",
            " truncate ",
            " create ",
            " grant ",
            " revoke ",
        ]
        if any(token in sql_lower for token in forbidden_tokens) or sql_lower.strip().startswith(
            ("insert", "update", "delete", "alter", "drop", "truncate", "create", "grant", "revoke")
        ):
            return False, "Only read-only (SELECT) queries are allowed for this sub-scheme."

        # If any sub_head_expenditure_ table is referenced, it must be this subscheme's table.
        if "sub_head_expenditure_" in sql_lower and self._TABLE_NAME not in sql_lower:
            return (
                False,
                "Query is attempting to access sub-head expenditure data outside the selected sub-scheme.",
            )

        return True, sql


POLICY: SubschemeSecurityPolicy = _Policy20750249()



