from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import re
import logging

from src.database import get_db
from src import models
from src.core.templates import templates
from src.email_service import validate_email, get_default_notification_preferences, EmailService
from src.utils_scheme import get_scheme_base_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui/s{scheme_code}/settings", tags=["Settings"], include_in_schema=False)


def validate_phone(phone: Optional[str]) -> bool:
    if not phone:
        return True
    phone_cleaned = re.sub(r'\D', '', phone)
    return len(phone_cleaned) == 10


@router.get("/profile", response_class=JSONResponse)
async def get_user_settings(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    auth_user = request.cookies.get('auth_user', '')
    if not auth_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user = db.query(models.User).filter(models.User.username == auth_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    prefs = user.notification_preferences
    if not prefs:
        prefs = get_default_notification_preferences()
    
    return JSONResponse({
        "email": user.email or "",
        "phone_number": user.phone_number or "",
        "notification_preferences": prefs
    })


@router.post("/profile", response_class=JSONResponse)
async def update_user_settings(
    request: Request,
    scheme_code: str,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    email = form_data.get('email', '').strip() or None
    phone_number = form_data.get('phone_number', '').strip() or None
    data_filling_period = form_data.get('data_filling_period', 'false').lower() == 'true'
    taluka_activation = form_data.get('taluka_activation', 'false').lower() == 'true'
    fiscal_year_changes = form_data.get('fiscal_year_changes', 'false').lower() == 'true'
    auth_user = request.cookies.get('auth_user', '')
    if not auth_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user = db.query(models.User).filter(models.User.username == auth_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    errors = []
    
    if email is not None:
        if email and not validate_email(email):
            errors.append("अवैध ईमेल पत्ता")
        else:
            user.email = email
    
    if phone_number is not None:
        if phone_number and not validate_phone(phone_number):
            errors.append("अवैध फोन नंबर (10 अंक आवश्यक)")
        else:
            phone_cleaned = re.sub(r'\D', '', phone_number) if phone_number else None
            user.phone_number = phone_cleaned
    
    prefs = user.notification_preferences or get_default_notification_preferences()
    prefs['data_filling_period'] = data_filling_period
    prefs['taluka_activation'] = taluka_activation
    prefs['fiscal_year_changes'] = fiscal_year_changes
    user.notification_preferences = prefs
    
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    try:
        db.commit()
        return JSONResponse({
            "success": True,
            "message": "सेटिंग्ज यशस्वीरित्या अपडेट केले"
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="सेटिंग्ज अपडेट करताना त्रुटी")


@router.post("/test-email", response_class=JSONResponse)
async def test_email(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    auth_user = request.cookies.get('auth_user', '')
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    
    if not auth_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if auth_level != 'dco' or auth_role != 'assistant':
        raise HTTPException(status_code=403, detail="Only DCO assistants can test email")
    
    user = db.query(models.User).filter(models.User.username == auth_user).first()
    if not user or not user.email:
        raise HTTPException(status_code=400, detail="User email not found")
    
    email_service = EmailService()
    
    html_body, text_body = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #0a0a0a; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .info-box { background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #0a0a0a; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Budget Management System</h2>
        </div>
        <div class="content">
            <h3>ईमेल चाचणी / Email Test</h3>
            <div class="info-box">
                <p><strong>हा एक चाचणी ईमेल आहे.</strong></p>
                <p>This is a test email to verify SMTP configuration.</p>
            </div>
            <p>जर आपल्याला हा ईमेल मिळाला असेल, तर SMTP कॉन्फिगरेशन योग्यरित्या कार्य करत आहे.</p>
        </div>
        <div class="footer">
            <p>या ईमेलसाठी उत्तर देऊ नका.</p>
        </div>
    </div>
</body>
</html>
""", "Budget Management System\nEmail Test\n\nThis is a test email to verify SMTP configuration.\n\nIf you received this email, SMTP configuration is working correctly."
    
    success = email_service.send_email(
        user.email,
        "ईमेल चाचणी / Email Test - Budget Management System",
        html_body,
        text_body
    )
    
    if success:
        return JSONResponse({
            "success": True,
            "message": f"Test email sent successfully to {user.email}"
        })
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check SMTP configuration.")


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request, scheme_code: str, db: Session = Depends(get_db)):
    auth_user = request.cookies.get('auth_user', '')
    if not auth_user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url='/', status_code=303)
    
    user = db.query(models.User).filter(models.User.username == auth_user).first()
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url='/', status_code=303)
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "resource_name": "सेटिंग्ज / Settings",
        "auth_level": request.cookies.get('auth_level', ''),
        "auth_role": request.cookies.get('auth_role', ''),
        "base_template": get_scheme_base_template(request),
        "scheme_code": scheme_code
    })
