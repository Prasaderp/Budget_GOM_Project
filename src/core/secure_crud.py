"""Secure CRUD factory with authentication and authorization.

Provides centralized, production-level API route generation with:
- Authentication enforcement on all mutating endpoints
- District-based access control for data isolation
- Role-based permission checks
- Integrated audit logging
- Input validation and sanitization

Note: Uses lazy imports to avoid circular dependencies.
"""
from types import SimpleNamespace
from typing import Collection, Type, TypeVar, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.orm import Session

T = TypeVar('T')


def _get_db():
    """Lazy import of get_db to avoid circular imports."""
    from src.database import get_db
    return get_db


def _require_auth(request: Request) -> str:
    """Validate authentication exists. Returns username or raises 401."""
    from src.utils_auth import get_auth_user
    username = get_auth_user(request)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return username


def _get_auth_context(request: Request) -> tuple:
    """Get auth context (level, unit, role) with lazy imports."""
    from src.utils_auth import get_auth_level, get_auth_role, get_auth_unit
    return get_auth_level(request), get_auth_unit(request), get_auth_role(request)


def _check_write_permission(request: Request, db: Session, sub_scheme_code: str) -> None:
    """Check if user has write permission. Raises 403 if denied."""
    from src.utils_district import check_edit_permission
    level, unit, role = _get_auth_context(request)
    if not check_edit_permission(role, level, unit, db, sub_scheme_code):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Write permission denied")


def _check_district_access(request: Request, db: Session, district: str) -> None:
    """Validate user can access the specified district. Raises 403 if denied."""
    from src.utils_district import validate_access_control
    level, unit, _ = _get_auth_context(request)
    allowed, error_msg = validate_access_control(district, level, unit, db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_msg or "Access denied")


def _get_item_or_404(model: Type[T], item_id: int, sub_scheme_code: str, db: Session) -> T:
    """Get item by ID or raise 404."""
    item = db.query(model).filter(model.id == item_id, model.sub_scheme_code == sub_scheme_code).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return item


def _build_district_filter(query, level: str, unit: str, model):
    """Build district filter with lazy import."""
    from src.utils_district import build_district_filter
    return build_district_filter(query, level, unit, model)


def _validate_fiscal_year(fiscal_year, db):
    """Validate fiscal year with lazy import."""
    from src.utils_fiscal_year import validate_fiscal_year
    return validate_fiscal_year(fiscal_year, db)


def _log_audit(db, request, action, table, record_id, old_values=None, new_values=None):
    """Log audit with lazy import."""
    from src.audit_service import AuditService
    AuditService.log_action(db, request, action, table, record_id, old_values=old_values, new_values=new_values)


def _serialize_values(obj):
    """Serialize model values with lazy import."""
    from src.audit_service import AuditService
    return AuditService.serialize_values(obj)


def create_secure_crud_routes(
    router: APIRouter,
    model: Type[T],
    create_schema: type,
    update_schema: type,
    response_schema: type,
    route_prefix: str,
    scheme_code: str,
    sub_scheme_code: str,
    district_field: str = "district",
    table_name: Optional[str] = None,
    methods: Optional[Collection[str]] = None,
) -> None:
    """Create secured CRUD routes with auth, access control, and audit logging."""
    from src.database import get_db

    configured_methods = (
        ("GET", "POST", "PUT", "DELETE") if methods is None else methods
    )
    enabled_methods = frozenset(method.upper() for method in configured_methods)
    invalid_methods = enabled_methods - {"GET", "POST", "PUT", "DELETE"}
    if invalid_methods:
        raise ValueError(f"Unsupported CRUD methods: {sorted(invalid_methods)}")

    def register_if(enabled, route_decorator):
        return route_decorator if enabled else lambda endpoint: endpoint

    audit_table = table_name or getattr(model, '__tablename__', route_prefix)

    @register_if(
        "GET" in enabled_methods,
        router.get(f"/{route_prefix}", response_model=List[response_schema]),
    )
    def list_items(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        fiscal_year: Optional[str] = None,
        db: Session = Depends(get_db)
    ):
        _require_auth(request)
        level, unit, _ = _get_auth_context(request)
        fy = _validate_fiscal_year(fiscal_year, db)
        query = db.query(model).filter(model.fiscal_year == fy, model.sub_scheme_code == sub_scheme_code)
        query = _build_district_filter(query, level, unit, model)
        return query.offset(skip).limit(min(limit, 500)).all()

    @register_if(
        "GET" in enabled_methods,
        router.get(f"/{route_prefix}/{{id}}", response_model=response_schema),
    )
    def get_item(request: Request, id: int, db: Session = Depends(get_db)):
        _require_auth(request)
        item = _get_item_or_404(model, id, sub_scheme_code, db)
        if hasattr(item, district_field):
            _check_district_access(request, db, getattr(item, district_field))
        return item

    @register_if(
        "POST" in enabled_methods,
        router.post(
            f"/{route_prefix}",
            response_model=response_schema,
            status_code=status.HTTP_201_CREATED,
        ),
    )
    def create_item(request: Request, data: create_schema, db: Session = Depends(get_db)):
        from src.core.derivation.registry import run_for
        from src.core.taluka.write import create_row_family

        _require_auth(request)
        _check_write_permission(request, db, sub_scheme_code)
        item_data = data.model_dump()
        if district_field in item_data:
            _check_district_access(request, db, item_data[district_field])
        item_data['fiscal_year'] = _validate_fiscal_year(item_data.get('fiscal_year'), db)
        item_data['scheme_code'] = scheme_code
        item_data['sub_scheme_code'] = sub_scheme_code
        db_item = create_row_family(db, model, item_data, request)
        run_for(db, model, db_item, request)
        _log_audit(db, request, 'INSERT', audit_table, db_item.id, new_values=item_data)
        db.commit()
        db.refresh(db_item)
        return db_item

    @register_if(
        "PUT" in enabled_methods,
        router.put(f"/{route_prefix}/{{id}}", response_model=response_schema),
    )
    def update_item(request: Request, id: int, data: update_schema, db: Session = Depends(get_db)):
        from src.core.derivation.registry import run_for
        from src.core.taluka.write import resolve_editable_row
        from src.core.taluka.consolidation import consolidate_row
        from src.core.taluka.models import natural_key_columns

        _require_auth(request)
        _check_write_permission(request, db, sub_scheme_code)
        db_item = resolve_editable_row(db, model, id, request)
        if db_item.sub_scheme_code != sub_scheme_code:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        old_values = _serialize_values(db_item)
        update_data = data.model_dump(exclude_unset=True)
        for protected in ('id', 'scheme_code', 'sub_scheme_code', 'fiscal_year', 'taluka', *natural_key_columns(model)):
            update_data.pop(protected, None)
        if district_field in update_data:
            _check_district_access(request, db, update_data[district_field])
        for key, value in update_data.items():
            setattr(db_item, key, value)
        db.flush()
        key_cols = natural_key_columns(model)
        natural_key = {c: getattr(db_item, c) for c in key_cols}
        consolidate_row(db, model, db_item.district, db_item.fiscal_year, natural_key)
        run_for(db, model, db_item, request)
        db.refresh(db_item)
        new_values = _serialize_values(db_item)
        _log_audit(db, request, 'UPDATE', audit_table, db_item.id, old_values=old_values, new_values=new_values)
        db.commit()
        return db_item

    @register_if(
        "DELETE" in enabled_methods,
        router.delete(f"/{route_prefix}/{{id}}", status_code=status.HTTP_204_NO_CONTENT),
    )
    def delete_item(request: Request, id: int, db: Session = Depends(get_db)):
        from src.core.derivation.registry import is_registered, run_for
        from src.core.taluka.consolidation import _active_taluka_values
        from src.core.taluka.constants import DISTRICT_OFFICE
        from src.core.taluka.write import delete_row_family

        _require_auth(request)
        _check_write_permission(request, db, sub_scheme_code)
        db_item = _get_item_or_404(model, id, sub_scheme_code, db)
        if hasattr(db_item, district_field):
            _check_district_access(request, db, getattr(db_item, district_field))
        old_values = _serialize_values(db_item)
        derivation_target = None
        derivation_talukas = ()
        if is_registered(model):
            derivation_target = SimpleNamespace(
                district=db_item.district,
                fiscal_year=db_item.fiscal_year,
                category=db_item.category,
            )
            derivation_talukas = (
                DISTRICT_OFFICE,
                *_active_taluka_values(db, db_item.district),
            )
        _log_audit(db, request, 'DELETE', audit_table, id, old_values=old_values)
        delete_row_family(db, model, id, request)
        for taluka in derivation_talukas:
            run_for(
                db,
                model,
                derivation_target,
                request,
                taluka=taluka,
            )
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
