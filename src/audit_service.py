from sqlalchemy.orm import Session
from fastapi import Request
import uuid
from typing import Any, Dict, Optional
from src.models import AuditLog
from src.utils_auth import get_auth_user, get_auth_level, get_auth_role, get_auth_unit


class AuditService:
    @staticmethod
    def get_client_info(request: Request) -> tuple:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host
        else:
            ip_address = "unknown"
        user_agent = request.headers.get("user-agent", "")[:500]
        return ip_address, user_agent

    @staticmethod
    def get_user_info(request: Request) -> tuple:
        username = get_auth_user(request) or "anonymous"
        level = get_auth_level(request) or "unknown"
        role = get_auth_role(request) or "unknown"
        unit = get_auth_unit(request) or ""
        session_id = request.cookies.get("session_id") or str(uuid.uuid4())[:8]
        return username, level, role, unit, session_id

    @staticmethod
    def serialize_values(obj: Any) -> Dict[str, Any]:
        if not hasattr(obj, '__table__'):
            return {}
        
        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name, None)
            if value is None:
                result[column.name] = None
            elif hasattr(value, 'isoformat'):
                result[column.name] = value.isoformat()
            elif isinstance(value, (dict, list)):
                result[column.name] = value
            else:
                result[column.name] = str(value)
        return result

    @staticmethod
    def get_changed_fields(old_values: Dict, new_values: Dict) -> list:
        all_keys = set(old_values.keys()) | set(new_values.keys())
        return [
            {'field': key, 'old_value': old_values.get(key), 'new_value': new_values.get(key)}
            for key in all_keys if old_values.get(key) != new_values.get(key)
        ]

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
        try:
            username, level, role, unit, session_id = AuditService.get_user_info(request)
            ip_address, user_agent = AuditService.get_client_info(request)
            
            changed_fields = None
            if old_values and new_values and action == 'UPDATE':
                changed_fields = AuditService.get_changed_fields(old_values, new_values)
                if not changed_fields:
                    return
            
            audit_entry = AuditLog(
                table_name=table_name,
                record_id=record_id,
                action=action,
                username=username,
                user_level=level,
                user_role=role,
                user_unit=unit,
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id
            )
            
            db.add(audit_entry)
            db.flush()
            
        except Exception:
            pass

    @staticmethod
    def log_create(db: Session, request: Request, obj: Any):
        table_name = obj.__table__.name
        record_id = getattr(obj, 'id', 0)
        new_values = AuditService.serialize_values(obj)
        
        AuditService.log_action(
            db=db,
            request=request,
            action='INSERT',
            table_name=table_name,
            record_id=record_id,
            new_values=new_values
        )

    @staticmethod
    def log_update(db: Session, request: Request, obj: Any, original_obj: Any = None):
        table_name = obj.__table__.name
        record_id = getattr(obj, 'id', 0)
        new_values = AuditService.serialize_values(obj)
        old_values = AuditService.serialize_values(original_obj) if original_obj else {}
        
        AuditService.log_action(
            db=db,
            request=request,
            action='UPDATE',
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values
        )

    @staticmethod
    def log_delete(db: Session, request: Request, obj: Any):
        table_name = obj.__table__.name
        record_id = getattr(obj, 'id', 0)
        old_values = AuditService.serialize_values(obj)
        
        AuditService.log_action(
            db=db,
            request=request,
            action='DELETE',
            table_name=table_name,
            record_id=record_id,
            old_values=old_values
        )

    @staticmethod
    def log_login(db: Session, request: Request, username: str):
        ip_address, user_agent = AuditService.get_client_info(request)
        
        audit_entry = AuditLog(
            table_name='users',
            record_id=0,
            action='LOGIN',
            username=username,
            user_level='unknown',
            user_role='unknown',
            user_unit='',
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=str(uuid.uuid4())[:8]
        )
        
        db.add(audit_entry)

    @staticmethod
    def log_edit(db: Session, request: Request, table_name: str, record_id: int, 
                 username: str, old_values: dict, new_values: dict):
        try:
            ip_address, user_agent = AuditService.get_client_info(request)
            _, level, role, unit, session_id = AuditService.get_user_info(request)
            changed = AuditService.get_changed_fields(old_values, new_values)
            if not changed:
                return
            audit_entry = AuditLog(
                table_name=table_name, record_id=record_id, action='UPDATE',
                username=username, user_level=level, user_role=role, user_unit=unit,
                old_values=old_values, new_values=new_values, changed_fields=changed,
                ip_address=ip_address, user_agent=user_agent[:500] if user_agent else '',
                session_id=session_id
            )
            db.add(audit_entry)
            db.flush()
        except Exception:
            pass

    @staticmethod
    def log_export(db: Session, request: Request, export_type: str, record_count: int = 0):
        username, level, role, unit, session_id = AuditService.get_user_info(request)
        ip_address, user_agent = AuditService.get_client_info(request)
        
        audit_entry = AuditLog(
            table_name=export_type,
            record_id=record_count,
            action='EXPORT',
            username=username,
            user_level=level,
            user_role=role,
            user_unit=unit,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            new_values={'export_type': export_type, 'record_count': record_count}
        )
        
        db.add(audit_entry)
