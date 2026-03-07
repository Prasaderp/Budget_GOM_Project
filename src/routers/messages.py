from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from html import escape as html_escape
from src.database import get_db
from src import models
from src import schemas
from src.utils_auth import get_auth_user

router = APIRouter(prefix="/api/messages", tags=["Messages"], include_in_schema=False)

@router.get("")
async def list_messages(thread_key: str, request: Request, db: Session = Depends(get_db)):
    from_user = get_auth_user(request)
    if not from_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = db.query(models.User).filter(
        models.User.username == from_user,
        (models.User.level != 'taluka') | (models.User.is_active == True)
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    parts = (thread_key or '').split(":", 2)
    keys = set()
    base_key = f"unified:{user.level}:{user.unit or ''}"
    keys.add(base_key)
    if user.level == 'taluka' and user.unit:
        if ' Taluka ' in user.unit:
            district = user.unit.split(' Taluka ')[0]
            keys.add(f"unified:district:{district}")
    if user.level in ('taluka','district'):
        keys.add(f"unified:dco:")
    if user.level == 'dco':
        keys.add(f"unified:dco:")
    base_filter = or_(models.Message.from_username == from_user, models.Message.to_username == from_user)
    
    if user.role == 'assistant':
        restricted_filter = ~(
            (models.Message.role_from == 'officer1') & (models.Message.role_to == 'officer2') |
            (models.Message.role_from == 'officer2') & (models.Message.role_to == 'officer1')
        )
        visibility_filter = base_filter & restricted_filter
    else:
        visibility_filter = base_filter
    
    items = (
        db.query(models.Message)
        .filter(models.Message.thread_key.in_(list(keys)))
        .filter(visibility_filter)
        .order_by(models.Message.created_at.asc())
        .limit(1000)
        .all()
    )
    response_data = [schemas.MessageResponse.model_validate(m).model_dump() for m in items]
    
    from fastapi import Response
    response = Response(content=str(response_data), media_type="application/json")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response_data

@router.get("/recipients")
async def list_recipients(request: Request, db: Session = Depends(get_db)):
    from_user = get_auth_user(request)
    if not from_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = db.query(models.User).filter(
        models.User.username == from_user,
        (models.User.level != 'taluka') | (models.User.is_active == True)
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    recipients = {}
    qs = []
    
    if user.level == 'dco':
        if user.role == 'dco':
            qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'officer1'))
        elif user.role == 'officer1':
            qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'dco'))
            qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'officer2'))
        elif user.role == 'officer2':
            qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'officer1'))
            qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'assistant'))
        elif user.role == 'assistant':
            from src.config import DCO_STAFF_IDENTIFIER
            qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'officer2'))
            qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.role == 'officer1'))
            qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.role == 'assistant'))
            qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == DCO_STAFF_IDENTIFIER, models.User.role == 'officer1'))
            qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == DCO_STAFF_IDENTIFIER, models.User.role == 'assistant'))
    
    elif user.level == 'district':
        from src.config import DCO_STAFF_IDENTIFIER
        if user.unit == DCO_STAFF_IDENTIFIER:
            if user.role == 'officer1':
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == DCO_STAFF_IDENTIFIER, models.User.role == 'officer2'))
                qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'assistant'))
            elif user.role == 'officer2':
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == DCO_STAFF_IDENTIFIER, models.User.role == 'officer1'))
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == DCO_STAFF_IDENTIFIER, models.User.role == 'assistant'))
            elif user.role == 'assistant':
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == DCO_STAFF_IDENTIFIER, models.User.role == 'officer2'))
                qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'assistant'))
        else:
            if user.role == 'officer1':
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == user.unit, models.User.role == 'officer2'))
                qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'assistant'))
            elif user.role == 'officer2':
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == user.unit, models.User.role == 'officer1'))
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == user.unit, models.User.role == 'assistant'))
            elif user.role == 'assistant':
                qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == user.unit, models.User.role == 'officer2'))
                qs.append(db.query(models.User).filter(models.User.level == 'dco', models.User.role == 'assistant'))
                qs.append(db.query(models.User).filter(models.User.level == 'taluka', models.User.unit.like(f"{user.unit} Taluka %"), models.User.role == 'officer1', models.User.is_active == True))
                qs.append(db.query(models.User).filter(models.User.level == 'taluka', models.User.unit.like(f"{user.unit} Taluka %"), models.User.role == 'assistant', models.User.is_active == True))
    
    elif user.level == 'taluka':
        if user.role == 'officer1':
            district = user.unit.split(' Taluka ')[0] if ' Taluka ' in user.unit else user.unit
            qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == district, models.User.role == 'assistant'))
            qs.append(db.query(models.User).filter(models.User.level == 'taluka', models.User.unit == user.unit, models.User.role == 'officer2', models.User.is_active == True))
        elif user.role == 'officer2':
            qs.append(db.query(models.User).filter(models.User.level == 'taluka', models.User.unit == user.unit, models.User.role == 'officer1', models.User.is_active == True))
            qs.append(db.query(models.User).filter(models.User.level == 'taluka', models.User.unit == user.unit, models.User.role == 'assistant', models.User.is_active == True))
        elif user.role == 'assistant':
            district = user.unit.split(' Taluka ')[0] if ' Taluka ' in user.unit else user.unit
            qs.append(db.query(models.User).filter(models.User.level == 'district', models.User.unit == district, models.User.role == 'assistant'))
            qs.append(db.query(models.User).filter(models.User.level == 'taluka', models.User.unit == user.unit, models.User.role == 'officer2', models.User.is_active == True))
    
    for q in qs:
        for u in q.all():
            if u.username == user.username:
                continue
            recipients[u.username] = {"username": u.username, "full_name": u.full_name or u.username, "level": u.level, "unit": u.unit, "role": u.role}
    
    response_data = list(recipients.values())
    
    from fastapi.responses import JSONResponse
    
    response = JSONResponse(content=response_data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

@router.post("")
async def send_message(payload: schemas.MessageCreate, request: Request, db: Session = Depends(get_db)):
    from_user = get_auth_user(request)
    if not from_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = db.query(models.User).filter(
        models.User.username == from_user,
        (models.User.level != 'taluka') | (models.User.is_active == True)
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    to_user = db.query(models.User).filter(
        models.User.username == payload.to_username,
        (models.User.level != 'taluka') | (models.User.is_active == True)
    ).first()
    if not to_user:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if to_user.username == user.username:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    allowed = False
    
    # DCO Level connections
    if user.level == 'dco' and to_user.level == 'dco':
        if (user.role == 'dco' and to_user.role == 'officer1') or (user.role == 'officer1' and to_user.role == 'dco'):
            allowed = True
        elif (user.role == 'officer1' and to_user.role == 'officer2') or (user.role == 'officer2' and to_user.role == 'officer1'):
            allowed = True
        elif (user.role == 'officer2' and to_user.role == 'assistant') or (user.role == 'assistant' and to_user.role == 'officer2'):
            allowed = True
    
    # DCO Assistant to District/DCO Staff connections
    elif user.role == 'assistant' and user.level == 'dco' and to_user.level == 'district':
        from src.config import DCO_STAFF_IDENTIFIER
        if to_user.role in ('officer1', 'assistant'):
            allowed = True
    elif user.level == 'district' and to_user.role == 'assistant' and to_user.level == 'dco':
        from src.config import DCO_STAFF_IDENTIFIER
        if user.role in ('officer1', 'assistant'):
            allowed = True
    
    # District Level connections (within same district) - includes DCO Staff
    elif user.level == 'district' and to_user.level == 'district' and user.unit == to_user.unit:
        from src.config import DCO_STAFF_IDENTIFIER
        if (user.role == 'officer1' and to_user.role == 'officer2') or (user.role == 'officer2' and to_user.role == 'officer1'):
            allowed = True
        elif (user.role == 'officer2' and to_user.role == 'assistant') or (user.role == 'assistant' and to_user.role == 'officer2'):
            allowed = True
    
    # District Assistant to Taluka connections (same district)
    elif user.role == 'assistant' and user.level == 'district' and to_user.level == 'taluka':
        if to_user.role in ('officer1', 'assistant') and to_user.unit.startswith(f"{user.unit} Taluka "):
            allowed = True
    elif user.level == 'taluka' and to_user.role == 'assistant' and to_user.level == 'district':
        if user.role in ('officer1', 'assistant') and user.unit.startswith(f"{to_user.unit} Taluka "):
            allowed = True
    
    # Taluka Level connections (within same taluka)
    elif user.level == 'taluka' and to_user.level == 'taluka' and user.unit == to_user.unit:
        if (user.role == 'officer1' and to_user.role == 'officer2') or (user.role == 'officer2' and to_user.role == 'officer1'):
            allowed = True
        elif (user.role == 'officer2' and to_user.role == 'assistant') or (user.role == 'assistant' and to_user.role == 'officer2'):
            allowed = True
    if not allowed:
        raise HTTPException(status_code=403, detail="Messaging not allowed between these roles or units")
    parts = payload.thread_key.split(":", 2)
    if user.level == to_user.level and (user.unit or '') == (to_user.unit or ''):
        norm_thread = f"unified:{user.level}:{user.unit or ''}"
    else:
        levels = {user.level, to_user.level}
        if 'taluka' in levels and 'district' in levels:
            if user.level == 'district':
                district = user.unit or ''
            else:
                district = (user.unit or '').split(' Taluka ')[0] if user.level == 'taluka' else (to_user.unit or '').split(' Taluka ')[0]
            norm_thread = f"unified:district:{district}"
        elif 'dco' in levels and 'district' in levels:
            norm_thread = f"unified:dco:"
        else:
            norm_thread = f"unified:{user.level}:{user.unit or ''}"
    msg = models.Message(
        thread_key=norm_thread,
        from_username=user.username,
        to_username=to_user.username,
        role_from=user.role,
        role_to=to_user.role,
        text=html_escape(payload.text.strip()[:2000]) if payload.text else ""
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return schemas.MessageResponse.model_validate(msg).model_dump()


