"""
Audit service for sub-scheme 20530028.

This module provides audit logging capabilities by delegating to the global
AuditService while adding async logging support specific to this sub-scheme.
"""
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from fastapi import Request

# Import global AuditService for delegation
from src.audit_service import AuditService as GlobalAuditService

# Thread pool for async audit operations (non-blocking)
_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s20530028")


class AuditService:
    """
    Audit service that delegates to global AuditService.
    
    Provides all standard audit methods via delegation, plus async logging
    capability for non-blocking audit operations in high-throughput scenarios.
    """
    
    # =========================================================================
    # DELEGATED METHODS - Forward to global AuditService
    # =========================================================================
    
    @staticmethod
    def log_action(
        db: Session,
        request: Request,
        action: str,
        table_name: str,
        record_id: int,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None
    ):
        """Log an action (CREATE, UPDATE, DELETE) - delegates to global service."""
        return GlobalAuditService.log_action(
            db, request, action, table_name, record_id, old_values, new_values
        )
    
    @staticmethod
    def log_edit(
        db: Session,
        request: Request,
        table_name: str,
        record_id: int,
        username: str,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any]
    ):
        """Log an edit operation - delegates to global service."""
        return GlobalAuditService.log_edit(
            db, request, table_name, record_id, username, old_values, new_values
        )
    
    @staticmethod
    def serialize_values(obj: Any) -> Dict[str, Any]:
        """Serialize ORM object to dict - delegates to global service."""
        return GlobalAuditService.serialize_values(obj)
    
    @staticmethod
    def get_changed_fields(old_values: Dict, new_values: Dict) -> list:
        """Get list of changed fields - delegates to global service."""
        return GlobalAuditService.get_changed_fields(old_values, new_values)
    
    @staticmethod
    def get_client_info(request: Request) -> tuple:
        """Get client IP and user agent - delegates to global service."""
        return GlobalAuditService.get_client_info(request)
    
    @staticmethod
    def get_user_info(request: Request) -> tuple:
        """Get user info from cookies - delegates to global service."""
        return GlobalAuditService.get_user_info(request)
    
    # =========================================================================
    # ASYNC LOGGING - Sub-scheme specific capability
    # =========================================================================
    
    @staticmethod
    def log_audit_async(
        table: str,
        record_id: int,
        username: str,
        old_vals: Dict[str, Any],
        new_vals: Dict[str, Any],
        req_info: Dict[str, str]
    ):
        """
        Non-blocking async audit logging using thread pool.
        
        Use this for inline update operations where immediate response is critical.
        The audit log is written in a background thread to avoid blocking the request.
        
        Args:
            table: Database table name
            record_id: ID of the record being audited
            username: Username performing the action
            old_vals: Previous field values
            new_vals: New field values  
            req_info: Request context (ip, ua, level, role, unit, sid)
        """
        def _write_audit():
            try:
                import os
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                from src.models import AuditLog
                
                db_url = os.getenv("DATABASE_URL", "")
                if not db_url:
                    return
                
                # Compute changed fields
                changed = [
                    {"field": k, "old": old_vals.get(k), "new": new_vals.get(k)}
                    for k in set(old_vals) | set(new_vals)
                    if old_vals.get(k) != new_vals.get(k)
                ]
                if not changed:
                    return
                
                # Create isolated session for async write
                engine = create_engine(db_url, pool_pre_ping=True, pool_size=1)
                SessionLocal = sessionmaker(bind=engine)
                session = SessionLocal()
                try:
                    entry = AuditLog(
                        table_name=table,
                        record_id=record_id,
                        action='UPDATE',
                        username=username,
                        user_level=req_info.get('level', ''),
                        user_role=req_info.get('role', ''),
                        user_unit=req_info.get('unit', ''),
                        old_values=old_vals,
                        new_values=new_vals,
                        changed_fields=changed,
                        ip_address=req_info.get('ip', ''),
                        user_agent=req_info.get('ua', '')[:500] if req_info.get('ua') else '',
                        session_id=req_info.get('sid', '')
                    )
                    session.add(entry)
                    session.commit()
                finally:
                    session.close()
                    engine.dispose()
            except Exception:
                pass  # Fail silently - audit should never break main flow
        
        # Submit to thread pool for async execution
        _audit_executor.submit(_write_audit)

