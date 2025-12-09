"""Repository for PayMatrix operations (shared across forms)"""
from sqlalchemy.orm import Session
from typing import List, Optional
from src.models import PayMatrix


class PayMatrixRepository:
    """Repository for PayMatrix database access"""
    
    def __init__(self, db: Session):
        """Initialize repository with database session"""
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
    
    def get_basic_pay(self, stage: str, level: int) -> Optional[PayMatrix]:
        """Get PayMatrix record for given stage and level"""
        try:
            return self.db.query(PayMatrix).filter(
                PayMatrix.stage == stage,
                PayMatrix.level == level
            ).first()
        except Exception as e:
            raise ConnectionError(f"Failed to fetch basic pay: {str(e)}")

