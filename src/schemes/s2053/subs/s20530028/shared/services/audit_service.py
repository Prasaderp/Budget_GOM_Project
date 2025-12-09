"""Audit service for async audit logging"""
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from src.models import AuditLog

_audit_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit_s20530028")


class AuditService:
    """Service for async audit logging"""
    
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
        Async audit logging using thread pool
        
        Args:
            table: Table name
            record_id: Record ID
            username: Username
            old_vals: Old values dict
            new_vals: New values dict
            req_info: Request info dict
        """
        try:
            db_url = os.getenv("DATABASE_URL", "")
            if not db_url:
                return
            
            engine = create_engine(db_url, pool_pre_ping=True, pool_size=1)
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                changed = [
                    {"field": k, "old": old_vals.get(k), "new": new_vals.get(k)}
                    for k in set(old_vals) | set(new_vals)
                    if old_vals.get(k) != new_vals.get(k)
                ]
                if not changed:
                    return
                
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
                    user_agent=req_info.get('ua', ''),
                    session_id=req_info.get('sid', '')
                )
                session.add(entry)
                session.commit()
            finally:
                session.close()
                engine.dispose()
        except Exception:
            pass  # Fail silently for audit logging

