"""Audit service for sub-scheme 20530313.

Delegates to global audit service with scheme-specific context.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_20530313")


class AuditService:
    """Scheme-specific audit operations."""

    SUB_SCHEME_CODE = "20530313"

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
    """Non-blocking async audit logging via thread pool."""

    def _write_audit():
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from src.models import AuditLog

            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                return

            engine = create_engine(database_url)
            SessionLocal = sessionmaker(bind=engine)
            db_session = SessionLocal()

            try:
                log_entry = AuditLog(
                    action="UPDATE",
                    table_name=table,
                    record_id=record_id,
                    username=username,
                    old_values=json.dumps(old_vals, default=str),
                    new_values=json.dumps(new_vals, default=str),
                    ip_address=req_info.get("ip", ""),
                    user_agent=req_info.get("user_agent", "")
                )
                db_session.add(log_entry)
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                logger.error(f"Async audit log error: {e}")
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Async audit setup error: {e}")

    _audit_executor.submit(_write_audit)
