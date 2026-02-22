"""Audit service for sub-scheme 20530387.

Delegates to global audit service with scheme-specific context.
"""
import logging
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_20530387")


class AuditService:
    """Scheme-specific audit operations."""

    SUB_SCHEME_CODE = "20530387"

    @staticmethod
    def log_action(
        db,
        request,
        action: str,
        table_name: str,
        record_id: int,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None
    ):
        """Log action to global audit service."""
        try:
            from src.audit_service import AuditService as GlobalAuditService
            GlobalAuditService.log_action(
                db=db,
                request=request,
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values
            )
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")

    @staticmethod
    def serialize_values(record) -> Dict[str, Any]:
        """Serialize model values for audit."""
        try:
            from src.audit_service import AuditService as GlobalAuditService
            return GlobalAuditService.serialize_values(record)
        except Exception:
            return {}


def log_audit_async(
    table: str,
    record_id: int,
    username: str,
    old_vals: Dict[str, Any],
    new_vals: Dict[str, Any],
    req_info: Dict[str, str]
):
    """Non-blocking async audit logging via thread pool.
    
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
                log_entry = AuditLog(
                    action="UPDATE",
                    table_name=table,
                    record_id=record_id,
                    username=username,
                    user_level=req_info.get("level", ""),
                    user_role=req_info.get("role", ""),
                    user_unit=req_info.get("unit", ""),
                    old_values=old_vals,
                    new_values=new_vals,
                    changed_fields=changed,
                    ip_address=req_info.get("ip", ""),
                    user_agent=req_info.get("ua", "")[:500] if req_info.get("ua") else "",
                    session_id=req_info.get("sid", "")
                )
                session.add(log_entry)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Async audit log error: {e}")
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Async audit setup error: {e}")

    _audit_executor.submit(_write_audit)
