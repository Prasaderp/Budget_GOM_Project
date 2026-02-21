from __future__ import annotations
from typing import Dict, Optional, Tuple, Any

from src.chatbot.security import SubschemeSecurityPolicy
from src.chatbot.security.policies import DivisionDistrictSecurityMixin

class _Policy76100158(DivisionDistrictSecurityMixin, SubschemeSecurityPolicy):
    def enforce_question(self, question: str, user_context: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        return self._enforce_division_question(question, user_context)

    def enforce_sql(self, sql: str, user_context: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        return self._enforce_district_sql_scope(sql, user_context)

POLICY: SubschemeSecurityPolicy = _Policy76100158()
