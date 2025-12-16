""""Security policy for subschema 2215 (Water Scarcity)."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from src.chatbot.security import SubschemeSecurityPolicy
from src.chatbot.security.policies import DivisionDistrictSecurityMixin


class _Policy2215(DivisionDistrictSecurityMixin, SubschemeSecurityPolicy):
    """
    Subschema-specific security rules for 2215.

    - Restricts division-level (Konkan Division) queries to elevated roles (DCO/admin).
    - Prevents district-level users from querying other districts.
    - Leaves finer-grained table scoping to the generic policy and SQL validator.
    """

    def enforce_question(
        self, question: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        # Reuse generic division-level protections.
        return self._enforce_division_question(question, user_context)

    def enforce_sql(
        self, sql: str, user_context: Optional[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        # Reuse generic district scoping protections.
        return self._enforce_district_sql_scope(sql, user_context)


POLICY: SubschemeSecurityPolicy = _Policy2215()


