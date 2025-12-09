"""Service for Pay Matrix operations"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from src.models import PayMatrix


class PayMatrixService:
    """Service for Pay Matrix lookups and calculations"""
    
    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db
    
    def get_stages(self) -> List[str]:
        """Get all distinct pay matrix stages, sorted"""
        try:
            stages = self.db.query(PayMatrix.stage).distinct().order_by(
                PayMatrix.stage
            ).all()
            sorted_stages = sorted(
                [s[0] for s in stages],
                key=lambda x: int(x.split('-')[1])
            )
            return sorted_stages
        except Exception as e:
            raise ConnectionError(f"Failed to fetch pay matrix stages: {str(e)}")
    
    def get_levels(self, stage: str) -> List[int]:
        """Get all levels for a given stage"""
        try:
            levels = self.db.query(PayMatrix.level).filter(
                PayMatrix.stage == stage
            ).order_by(PayMatrix.level).all()
            return [l[0] for l in levels]
        except Exception as e:
            raise ConnectionError(f"Failed to fetch pay matrix levels: {str(e)}")
    
    def get_basic_pay(self, stage: str, level: int) -> Optional[Dict[str, any]]:
        """
        Get basic pay for given stage and level
        
        Returns:
            Dict with 'found', 'basic_pay' (in thousands), 'basic_pay_full' (full amount)
            or None if not found
        """
        try:
            record = self.db.query(PayMatrix).filter(
                PayMatrix.stage == stage,
                PayMatrix.level == level
            ).first()
            
            if not record:
                return {"found": False, "basic_pay": 0, "basic_pay_full": 0}
            
            basic_pay_thousands = record.basic_pay // 1000
            return {
                "found": True,
                "basic_pay": basic_pay_thousands,
                "basic_pay_full": record.basic_pay
            }
        except Exception as e:
            raise ConnectionError(f"Failed to fetch basic pay: {str(e)}")

