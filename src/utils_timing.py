from sqlalchemy.orm import Session
from src import models
from datetime import datetime
from typing import Optional, Tuple
from src.utils_cache import memory_cache

_TIMING_CACHE_TTL = 30  # seconds


def _get_active_period(db: Session, user_level: str):
    cache_key = f"timing_period:{user_level}"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return cached
    
    period = db.query(
        models.DataFillingPeriod.start_date,
        models.DataFillingPeriod.end_date
    ).filter(
        models.DataFillingPeriod.is_active == True,
        (models.DataFillingPeriod.level == user_level) | 
        (models.DataFillingPeriod.level == 'both')
    ).order_by(models.DataFillingPeriod.created_at.desc()).first()
    
    memory_cache.set(cache_key, period, _TIMING_CACHE_TTL)
    return period


def invalidate_timing_cache():
    for level in ['district', 'taluka', 'both']:
        memory_cache.delete(f"timing_period:{level}")


def check_data_filling_allowed(db: Session, user_level: str, user_role: str) -> Tuple[bool, Optional[str]]:
    if user_role != 'assistant' or user_level not in ['district', 'taluka']:
        return True, None
    
    period = _get_active_period(db, user_level)
    if not period:
        return True, None
    
    now = datetime.now()
    if now < period.start_date:
        return False, f"डेटा भरण कालावधी {period.start_date.strftime('%d-%m-%Y %H:%M')} ला सुरू होईल"
    
    if now > period.end_date:
        return False, f"डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपला"
    
    return True, None


def get_timing_warning_message(db: Session, user_level: str) -> Optional[str]:
    if user_level not in ['district', 'taluka']:
        return None
    
    period = _get_active_period(db, user_level)
    if not period:
        return None
    
    now = datetime.now()
    
    if now < period.start_date:
        return f"⚠️ डेटा भरण कालावधी {period.start_date.strftime('%d-%m-%Y %H:%M')} ते {period.end_date.strftime('%d-%m-%Y %H:%M')} | सध्या डेटा संपादन निष्क्रिय आहे"
    
    if now > period.end_date:
        return f"⚠️ डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपला | डेटा संपादन आता निष्क्रिय आहे"
    
    remaining_hours = (period.end_date - now).total_seconds() / 3600
    if remaining_hours < 24:
        return f"⚠️ डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपेल | 24 तासांपेक्षा कमी वेळ शिल्लक आहे!"
    
    return f"📅 डेटा भरण कालावधी: {period.start_date.strftime('%d-%m-%Y')} ते {period.end_date.strftime('%d-%m-%Y %H:%M')}"
