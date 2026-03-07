from sqlalchemy.orm import Session
from src import models
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
from src.utils_cache import memory_cache

_IST = ZoneInfo("Asia/Kolkata")


def _now_ist() -> datetime:
    return datetime.now(_IST).replace(tzinfo=None)

_TIMING_CACHE_TTL = 30  # seconds


def _get_active_period(db: Session, user_level: str, sub_scheme_code: Optional[str] = None):
    cache_key = f"timing_period:{sub_scheme_code or 'global'}:{user_level}"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return cached
    
    query = db.query(
        models.DataFillingPeriod.start_date,
        models.DataFillingPeriod.end_date
    ).filter(
        models.DataFillingPeriod.is_active == True,
        (models.DataFillingPeriod.level == user_level) | 
        (models.DataFillingPeriod.level == 'both')
    )
    
    if sub_scheme_code:
        query = query.filter(models.DataFillingPeriod.sub_scheme_code == sub_scheme_code)
    
    period = query.order_by(models.DataFillingPeriod.created_at.desc()).first()
    
    memory_cache.set(cache_key, period, _TIMING_CACHE_TTL)
    return period


def invalidate_timing_cache(sub_scheme_code: Optional[str] = None):
    for level in ['district', 'taluka', 'both']:
        if sub_scheme_code:
            memory_cache.delete(f"timing_period:{sub_scheme_code}:{level}")
        else:
            memory_cache.delete(f"timing_period:global:{level}")


def check_data_filling_allowed(db: Session, user_level: str, user_role: str, sub_scheme_code: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    if user_role != 'assistant' or user_level not in ['district', 'taluka']:
        return True, None
    
    period = _get_active_period(db, user_level, sub_scheme_code)
    if not period:
        return True, None
    
    now = _now_ist()
    if now < period.start_date:
        return False, f"डेटा भरण कालावधी {period.start_date.strftime('%d-%m-%Y %H:%M')} ला सुरू होईल"

    if now > period.end_date:
        return False, f"डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपला"

    return True, None


def get_timing_warning_message(db: Session, user_level: str, sub_scheme_code: Optional[str] = None) -> Optional[str]:
    if user_level not in ['district', 'taluka']:
        return None
    
    period = _get_active_period(db, user_level, sub_scheme_code)
    if not period:
        return None
    
    now = _now_ist()

    if now < period.start_date:
        return f"⚠️ डेटा भरण कालावधी {period.start_date.strftime('%d-%m-%Y %H:%M')} ते {period.end_date.strftime('%d-%m-%Y %H:%M')} | सध्या डेटा संपादन निष्क्रिय आहे"

    if now > period.end_date:
        return f"⚠️ डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपला | डेटा संपादन आता निष्क्रिय आहे"

    remaining_hours = (period.end_date - now).total_seconds() / 3600
    if remaining_hours < 24:
        return f"⚠️ डेटा भरण कालावधी {period.end_date.strftime('%d-%m-%Y %H:%M')} ला संपेल | 24 तासांपेक्षा कमी वेळ शिल्लक आहे!"

    return f"📅 डेटा भरण कालावधी: {period.start_date.strftime('%d-%m-%Y')} ते {period.end_date.strftime('%d-%m-%Y %H:%M')}"
