"""Audit service for sub-scheme 20530242.

Provides audit logging by delegating to global AuditService with
async logging support for high-throughput scenarios.
"""
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from fastapi import Request

from src.audit_service import AuditService as GlobalAuditService

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s20530242")


class AuditService:
    """Audit service delegating to global AuditService."""

    @staticmethod
    def log_action(
        db: Session, request: Request, action: str, table_name: str,
        record_id: int, old_values: Optional[Dict] = None, new_values: Optional[Dict] = None
    ):
        """Log action - delegates to global service."""
        return GlobalAuditService.log_action(db, request, action, table_name, record_id, old_values, new_values)

    @staticmethod
    def log_edit(
        db: Session, request: Request, table_name: str, record_id: int,
        username: str, old_values: Dict[str, Any], new_values: Dict[str, Any]
    ):
        """Log edit - delegates to global service."""
        return GlobalAuditService.log_edit(db, request, table_name, record_id, username, old_values, new_values)

    @staticmethod
    def serialize_values(obj: Any) -> Dict[str, Any]:
        """Serialize ORM object to dict."""
        return GlobalAuditService.serialize_values(obj)

    @staticmethod
    def get_changed_fields(old_values: Dict, new_values: Dict) -> list:
        """Get list of changed fields."""
        return GlobalAuditService.get_changed_fields(old_values, new_values)

    @staticmethod
    def get_client_info(request: Request) -> tuple:
        """Get client IP and user agent."""
        return GlobalAuditService.get_client_info(request)

    @staticmethod
    def get_user_info(request: Request) -> tuple:
        """Get user info from cookies."""
        return GlobalAuditService.get_user_info(request)

    @staticmethod
    def log_audit_async(
        table: str, record_id: int, username: str,
        old_vals: Dict[str, Any], new_vals: Dict[str, Any], req_info: Dict[str, str]
    ):
        """Non-blocking async audit logging using thread pool.
        
        Reuses the app's existing connection pool via src.database.SessionLocal.
        """
        def _write_audit():
            try:
                from src.database import SessionLocal
                from src.models import AuditLog

                changed = [
                    {"field": k, "old": old_vals.get(k), "new": new_vals.get(k)}
                    for k in set(old_vals) | set(new_vals)
                    if old_vals.get(k) != new_vals.get(k)
                ]
                if not changed:
                    return

                session = SessionLocal()
                try:
                    entry = AuditLog(
                        table_name=table, record_id=record_id, action='UPDATE',
                        username=username, user_level=req_info.get('level', ''),
                        user_role=req_info.get('role', ''), user_unit=req_info.get('unit', ''),
                        old_values=old_vals, new_values=new_vals, changed_fields=changed,
                        ip_address=req_info.get('ip', ''),
                        user_agent=req_info.get('ua', '')[:500] if req_info.get('ua') else '',
                        session_id=req_info.get('sid', '')
                    )
                    session.add(entry)
                    session.commit()
                finally:
                    session.close()
            except Exception:
                pass

        _audit_executor.submit(_write_audit)
