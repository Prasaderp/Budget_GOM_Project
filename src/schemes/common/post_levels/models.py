"""SQLAlchemy model for post level details"""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, Numeric, CheckConstraint, UniqueConstraint, DateTime
from sqlalchemy.sql import func
from src.database import Base


class PostLevelDetail(Base):
    """Model for storing individual level details within a budget post"""
    __tablename__ = "post_level_details"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Parent reference (generic across subschemes)
    table_name = Column(String(100), nullable=False, index=True)
    budget_post_id = Column(Integer, nullable=False, index=True)
    sub_scheme_code = Column(String(15), nullable=False, index=True)
    fiscal_year = Column(CHAR(7), nullable=False, default='2025-26', server_default='2025-26', index=True)
    
    # Level identification
    level_name = Column(String(100), nullable=False)
    level_order = Column(Integer, nullable=False, default=1, server_default='1')
    
    # Pay Matrix reference
    pay_stage = Column(String(5), nullable=True)
    pay_level = Column(Integer, nullable=True)
    
    # Salary components (stored in thousands, matching parent table format)
    special_pay = Column(BigInteger, nullable=False, default=0, server_default='0')
    basic_pay = Column(Numeric(10, 1), nullable=False, default=0, server_default='0')
    grade_pay = Column(BigInteger, nullable=False, default=0, server_default='0')
    
    # Allowances (in thousands)
    local_supplementary_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    vehicle_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    washing_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    cash_allowance = Column(BigInteger, nullable=False, default=0, server_default='0')
    footwear_allowance_other = Column(BigInteger, nullable=False, default=0, server_default='0')
    
    # HRA rate
    hra_rate = Column(CHAR(1), nullable=False, default='X', server_default='X')
    
    # Audit timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('table_name', 'budget_post_id', 'sub_scheme_code', 'level_name',
                         name='uq_pld_level_name'),
        CheckConstraint("hra_rate IN ('X', 'Y', 'Z')", name='chk_pld_hra_rate'),
        CheckConstraint('basic_pay >= 0', name='chk_pld_basic_pay'),
        CheckConstraint('level_order > 0', name='chk_pld_level_order'),
    )

