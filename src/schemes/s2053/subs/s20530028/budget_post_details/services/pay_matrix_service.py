"""Service for Pay Matrix operations"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from src.models import PayMatrix


class PayMatrixService:
    """Service for Pay Matrix lookups and calculations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_stages(self) -> List[str]:
        """Get all distinct pay matrix stages, sorted"""
        stages = self.db.query(PayMatrix.stage).distinct().order_by(PayMatrix.stage).all()
        return sorted([s[0] for s in stages], key=lambda x: int(x.split('-')[1]))
    
    def get_levels(self, stage: str) -> List[int]:
        """Get all levels for a given stage"""
        levels = self.db.query(PayMatrix.level).filter(
            PayMatrix.stage == stage
        ).order_by(PayMatrix.level).all()
        return [l[0] for l in levels]
    
    def get_basic_pay(self, stage: str, level: int, salary_mode: str = 'monthly') -> Optional[Dict[str, any]]:
        """Get basic pay for given stage and level, optionally annualized"""
        record = self.db.query(PayMatrix).filter(
            PayMatrix.stage == stage,
            PayMatrix.level == level
        ).first()
        
        if not record:
            return {"found": False, "basic_pay": 0, "basic_pay_full": 0}
        
        multiplier = 12 if salary_mode == 'annual' else 1
        basic_pay_full = record.basic_pay * multiplier
        basic_pay_thousands = basic_pay_full // 1000
        
        return {
            "found": True,
            "basic_pay": basic_pay_thousands,
            "basic_pay_full": basic_pay_full,
            "salary_mode": salary_mode
        }

