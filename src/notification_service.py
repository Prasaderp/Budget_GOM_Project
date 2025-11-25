from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timezone, timedelta
import logging
import html
from src import models
from src.email_service import EmailService
from src.config import DCO_STAFF_IDENTIFIER
from src.database import SessionLocal

logger = logging.getLogger(__name__)
email_service = EmailService()

IST = timezone(timedelta(hours=5, minutes=30))


def _get_preference(user: models.User, preference_key: str) -> bool:
    prefs = user.notification_preferences
    if not prefs:
        return True
    return prefs.get(preference_key, True)


def _should_send_notification(user: models.User, preference_key: str) -> bool:
    if not user.is_active or not user.email:
        return False
    return _get_preference(user, preference_key)


def _to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def _format_datetime(dt: datetime) -> str:
    ist_dt = _to_ist(dt)
    return ist_dt.strftime('%d-%m-%Y %H:%M IST')


def _format_remaining_time(end_date: datetime) -> str:
    now = datetime.now(IST)
    end_ist = _to_ist(end_date)
    
    if end_ist < now:
        return "कालावधी संपला आहे"
    
    remaining = end_ist - now
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    
    if days > 0:
        return f"{days} दिवस, {hours} तास"
    elif hours > 0:
        return f"{hours} तास, {minutes} मिनिटे"
    else:
        return f"{minutes} मिनिटे"


def _escape_html(text: str) -> str:
    return html.escape(str(text))


def _create_email_template(title: str, content_html: str, header_color: str = "#0a0a0a") -> Tuple[str, str]:
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {header_color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid {header_color}; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Budget Management System</h2>
        </div>
        <div class="content">
            {content_html}
        </div>
        <div class="footer">
            <p>या ईमेलसाठी उत्तर देऊ नका.</p>
        </div>
    </div>
</body>
</html>
"""
    
    text_template = f"""
Budget Management System
{'=' * 50}

{title}

{content_html.replace('<h3>', '').replace('</h3>', '').replace('<p>', '').replace('</p>', '\n').replace('<strong>', '').replace('</strong>', '').replace('<div class="info-box">', '').replace('</div>', '').replace('&nbsp;', ' ')}

या ईमेलसाठी उत्तर देऊ नका.
"""
    
    return html_template, text_template


def send_data_filling_period_alert(
    db: Optional[Session],
    period: models.DataFillingPeriod,
    action_type: str
) -> Tuple[int, int]:
    db_session = None
    try:
        if db is None:
            db_session = SessionLocal()
            db = db_session
        affected_levels = []
        if period.level == 'both':
            affected_levels = ['district', 'taluka']
        elif period.level == 'district':
            affected_levels = ['district']
        elif period.level == 'taluka':
            affected_levels = ['taluka']
        
        if not affected_levels:
            logger.info(f"No affected levels for period: {period.level}")
            return (0, 0)
        
        query = db.query(models.User).filter(
            models.User.is_active == True,
            models.User.email.isnot(None),
            models.User.role == 'assistant'
        )
        
        if 'district' in affected_levels:
            query = query.filter(
                (models.User.level == 'district') | (models.User.level == 'dco')
            )
        else:
            query = query.filter(models.User.level.in_(affected_levels))
        
        users = query.all()
        
        if not users:
            logger.info(f"No users found for data filling period alert: level={period.level}")
            return (0, 0)
        
        unique_emails: Set[str] = set()
        recipients = []
        
        level_display = {
            'district': 'जिल्हा',
            'taluka': 'तालुका',
            'both': 'जिल्हा आणि तालुका'
        }
        
        action_display = {
            'created': 'सेट केले',
            'updated': 'अपडेट केले'
        }
        
        subject = f"डेटा भरण कालावधी {action_display.get(action_type, 'सेट केले')} - Budget Management System"
        
        for user in users:
            if not _should_send_notification(user, 'data_filling_period'):
                continue
            
            if user.email in unique_emails:
                continue
            
            unique_emails.add(user.email)
            
            level_text = level_display.get(period.level, period.level)
            remaining_time_text = _format_remaining_time(period.end_date)
            
            content_html = f"""
            <h3>डेटा भरण कालावधी {action_display.get(action_type, 'सेट केले')}</h3>
            <div class="info-box">
                <p><strong>स्तर:</strong> {_escape_html(level_text)}</p>
                <p><strong>प्रारंभ तारीख:</strong> {_format_datetime(period.start_date)}</p>
                <p><strong>समाप्ती तारीख:</strong> {_format_datetime(period.end_date)}</p>
                <p><strong>उर्वरित वेळ:</strong> {remaining_time_text}</p>
            </div>
            <p>कृपया या कालावधीत डेटा प्रविष्ट करा.</p>
            """
            
            html_body, text_body = _create_email_template(
                f"डेटा भरण कालावधी {action_display.get(action_type, 'सेट केले')}",
                content_html
            )
            
            recipients.append((user.email, subject, html_body, text_body))
        
        if not recipients:
            logger.info("No recipients after filtering preferences")
            return (0, 0)
        
        success, failure = email_service.send_batch_emails(recipients)
        logger.info(f"Data filling period alert: {success} succeeded, {failure} failed out of {len(recipients)} recipients")
        return (success, failure)
        
    except Exception as e:
        logger.error(f"Error sending data filling period alert: {e}", exc_info=True)
        return (0, 0)
    finally:
        if db_session:
            db_session.close()


def send_taluka_activation_alert(
    db: Optional[Session],
    district: str,
    taluka_name: str,
    users: Dict[str, models.User]
) -> Tuple[int, int]:
    db_session = None
    try:
        if db is None:
            db_session = SessionLocal()
            db = db_session
        recipients_list = []
        unique_emails: Set[str] = set()
        
        for role, user in users.items():
            if user and _should_send_notification(user, 'taluka_activation'):
                if user.email in unique_emails:
                    continue
                unique_emails.add(user.email)
                recipients_list.append((user, role))
        
        if not recipients_list:
            logger.info(f"No recipients for taluka activation alert: {taluka_name}")
            return (0, 0)
        
        subject = f"तालुका सक्रिय केला - {_escape_html(taluka_name)}"
        
        role_display = {
            'officer1': 'Officer 1',
            'officer2': 'Officer 2',
            'assistant': 'Assistant'
        }
        
        email_recipients = []
        
        for user, role in recipients_list:
            content_html = f"""
            <h3>तालुका सक्रिय केला</h3>
            <div class="info-box">
                <p><strong>जिल्हा:</strong> {_escape_html(district)}</p>
                <p><strong>तालुका:</strong> {_escape_html(taluka_name)}</p>
                <p><strong>आपली भूमिका:</strong> {_escape_html(role_display.get(role, role))}</p>
                <p><strong>वापरकर्तानाव:</strong> {_escape_html(user.username)}</p>
            </div>
            <p>आपला तालुका यशस्वीरित्या सक्रिय करण्यात आला आहे. आता आपण सिस्टम वापरू शकता.</p>
            """
            
            html_body, text_body = _create_email_template(
                "तालुका सक्रिय केला",
                content_html
            )
            
            email_recipients.append((user.email, subject, html_body, text_body))
        
        success, failure = email_service.send_batch_emails(email_recipients)
        logger.info(f"Taluka activation alert for {taluka_name}: {success} succeeded, {failure} failed")
        return (success, failure)
        
    except Exception as e:
        logger.error(f"Error sending taluka activation alert: {e}", exc_info=True)
        return (0, 0)
    finally:
        if db_session:
            db_session.close()


def send_taluka_deactivation_alert(
    db: Optional[Session],
    district: str,
    taluka_name: str,
    users: List[models.User]
) -> Tuple[int, int]:
    db_session = None
    try:
        if db is None:
            db_session = SessionLocal()
            db = db_session
        recipients_list = []
        unique_emails: Set[str] = set()
        
        for user in users:
            if user and _should_send_notification(user, 'taluka_activation'):
                if user.email in unique_emails:
                    continue
                unique_emails.add(user.email)
                recipients_list.append(user)
        
        if not recipients_list:
            logger.info(f"No recipients for taluka deactivation alert: {taluka_name}")
            return (0, 0)
        
        subject = f"तालुका निष्क्रिय केला - {_escape_html(taluka_name)}"
        
        email_recipients = []
        
        for user in recipients_list:
            content_html = f"""
            <h3>तालुका निष्क्रिय केला</h3>
            <div class="info-box">
                <p><strong>जिल्हा:</strong> {_escape_html(district)}</p>
                <p><strong>तालुका:</strong> {_escape_html(taluka_name)}</p>
            </div>
            <p>आपला तालुका निष्क्रिय करण्यात आला आहे. कृपया जिल्हा Assistant शी संपर्क साधा.</p>
            """
            
            html_body, text_body = _create_email_template(
                "तालुका निष्क्रिय केला",
                content_html,
                header_color="#dc2626"
            )
            
            email_recipients.append((user.email, subject, html_body, text_body))
        
        success, failure = email_service.send_batch_emails(email_recipients)
        logger.info(f"Taluka deactivation alert for {taluka_name}: {success} succeeded, {failure} failed")
        return (success, failure)
        
    except Exception as e:
        logger.error(f"Error sending taluka deactivation alert: {e}", exc_info=True)
        return (0, 0)
    finally:
        if db_session:
            db_session.close()


def send_fiscal_year_alert(
    db: Optional[Session],
    fiscal_year: models.FiscalYear,
    action_type: str
) -> Tuple[int, int]:
    db_session = None
    try:
        if db is None:
            db_session = SessionLocal()
            db = db_session
        users = db.query(models.User).filter(
            models.User.is_active == True,
            models.User.email.isnot(None)
        ).all()
        
        if not users:
            logger.info("No users found for fiscal year alert")
            return (0, 0)
        
        action_display = {
            'created': 'तयार केले',
            'deleted': 'हटवले'
        }
        
        subject = f"आर्थिक वर्ष {action_display.get(action_type, 'बदलले')} - {_escape_html(fiscal_year.year_range)}"
        
        unique_emails: Set[str] = set()
        email_recipients = []
        
        for user in users:
            if not _should_send_notification(user, 'fiscal_year_changes'):
                continue
            
            if user.email in unique_emails:
                continue
            
            unique_emails.add(user.email)
            
            status_text = 'सक्रिय' if fiscal_year.is_active else 'निष्क्रिय'
            
            content_html = f"""
            <h3>आर्थिक वर्ष {action_display.get(action_type, 'बदलले')}</h3>
            <div class="info-box">
                <p><strong>आर्थिक वर्ष:</strong> {_escape_html(fiscal_year.year_range)}</p>
                <p><strong>स्थिती:</strong> {status_text}</p>
            </div>
            <p>सिस्टममध्ये आर्थिक वर्ष {action_display.get(action_type, 'बदलले')} गेले आहे.</p>
            """
            
            html_body, text_body = _create_email_template(
                f"आर्थिक वर्ष {action_display.get(action_type, 'बदलले')}",
                content_html
            )
            
            email_recipients.append((user.email, subject, html_body, text_body))
        
        if not email_recipients:
            logger.info("No recipients after filtering preferences")
            return (0, 0)
        
        success, failure = email_service.send_batch_emails(email_recipients)
        logger.info(f"Fiscal year alert: {success} succeeded, {failure} failed out of {len(email_recipients)} recipients")
        return (success, failure)
        
    except Exception as e:
        logger.error(f"Error sending fiscal year alert: {e}", exc_info=True)
        return (0, 0)
    finally:
        if db_session:
            db_session.close()
