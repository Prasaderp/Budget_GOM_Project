from sqlalchemy.orm import Session
from src import models
from datetime import datetime
from typing import Optional, Tuple


def check_data_filling_allowed(db: Session, user_level: str, user_role: str) -> Tuple[bool, Optional[str]]:
    """
    Check if data filling/editing is allowed for the given user level and role.
    Returns (is_allowed, message)
    """
    if user_role not in ['assistant']:
        return True, None
    
    if user_level not in ['district', 'taluka']:
        return True, None
    
    now = datetime.now()
    
    period = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.is_active == True,
        ((models.DataFillingPeriod.level == user_level) | 
         (models.DataFillingPeriod.level == 'both'))
    ).order_by(models.DataFillingPeriod.created_at.desc()).first()
    
    if not period:
        return True, None
    
    if now < period.start_date:
        return False, f"डेटा भरण कालावधी {period.start_date.strftime('%d-%m-%Y %H:%M')} ला सुरू होईल"
    
    if now > period.end_date:
        return False, f"डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपला"
    
    return True, None


def get_timing_warning_message(db: Session, user_level: str) -> Optional[str]:
    """
    Get warning message for district/taluka level users about data filling periods.
    Returns message string or None.
    """
    if user_level not in ['district', 'taluka']:
        return None
    
    now = datetime.now()
    
    period = db.query(models.DataFillingPeriod).filter(
        models.DataFillingPeriod.is_active == True,
        ((models.DataFillingPeriod.level == user_level) | 
         (models.DataFillingPeriod.level == 'both'))
    ).order_by(models.DataFillingPeriod.created_at.desc()).first()
    
    if not period:
        return None
    
    if now < period.start_date:
        return f"⚠️ डेटा भरण कालावधी {period.start_date.strftime('%d-%m-%Y %H:%M')} ते {period.end_date.strftime('%d-%m-%Y %H:%M')} | सध्या डेटा संपादन निष्क्रिय आहे"
    
    if now > period.end_date:
        return f"⚠️ डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपला | डेटा संपादन आता निष्क्रिय आहे"
    
    remaining_hours = (period.end_date - now).total_seconds() / 3600
    
    if remaining_hours < 24:
        return f"⚠️ डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपेल | 24 तासांपेक्षा कमी वेळ शिल्लक आहे!"
    
    return f"📅 डेटा भरण कालावधी: {period.start_date.strftime('%d-%m-%Y')} ते {period.end_date.strftime('%d-%m-%Y %H:%M')}"

