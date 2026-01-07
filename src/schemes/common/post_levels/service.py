"""Service for post level business logic and aggregation"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from .repository import PostLevelRepository
from .schemas import (
    PostLevelCreate, PostLevelUpdate, PostLevelResponse,
    AggregatedTotals, PostLevelCalculateRequest, PostLevelCalculateResponse
)
from .models import PostLevelDetail


class PostLevelService:
    """Service for post level operations and salary calculations"""
    
    # Constants for calculations
    HRA_RATES = {'X': 0.30, 'Y': 0.20, 'Z': 0.10}
    DEFAULT_DA_RATE = 0.64  # Fallback if fiscal year not provided
    
    def __init__(self, db: Session, fiscal_year: Optional[str] = None):
        """Initialize service with database session and fiscal year
        
        Args:
            db: Database session
            fiscal_year: Fiscal year for DA rate lookup (format: 'YYYY-YY')
                        If None, uses default 64% DA rate
        """
        self.db = db
        self.repository = PostLevelRepository(db)
        self.fiscal_year = fiscal_year
        self._da_rate_cache: Optional[float] = None
    
    @property
    def da_rate(self) -> float:
        """Get DA rate for fiscal year (cached per instance)
        
        Returns:
            float: DA rate as decimal (e.g., 0.64 for 64%, 0.70 for 70%)
        """
        if self._da_rate_cache is None:
            from src.utils_da_rate import get_da_rate
            self._da_rate_cache = get_da_rate(self.db, self.fiscal_year)
        return self._da_rate_cache
    
    def calculate_dearness_allowance(self, basic_pay: float, grade_pay: int) -> int:
        """Calculate DA: (basic_pay + grade_pay) × DA rate (fiscal year specific)
        
        Args:
            basic_pay: Basic pay amount
            grade_pay: Grade pay amount
            
        Returns:
            int: Calculated dearness allowance amount
        """
        base = int(basic_pay) + int(grade_pay)
        return round(base * self.da_rate)
    
    def calculate_hra(self, basic_pay: float, grade_pay: int, hra_rate: str) -> int:
        """Calculate HRA: (basic_pay + grade_pay) × rate
        
        Args:
            basic_pay: Basic pay amount
            grade_pay: Grade pay amount
            hra_rate: HRA rate category ('X', 'Y', or 'Z')
            
        Returns:
            int: Calculated HRA amount
        """
        base = int(basic_pay) + int(grade_pay)
        rate = self.HRA_RATES.get(hra_rate, 0.30)
        return round(base * rate)
    
    def calculate_allowances(self, request: PostLevelCalculateRequest) -> PostLevelCalculateResponse:
        """Calculate DA and HRA for given inputs (API endpoint helper)"""
        base = int(request.basic_pay) + int(request.grade_pay)
        da = self.calculate_dearness_allowance(request.basic_pay, request.grade_pay)
        hra = self.calculate_hra(request.basic_pay, request.grade_pay, request.hra_rate)
        
        return PostLevelCalculateResponse(
            dearness_allowance=da,
            hra_amount=hra,
            base_for_allowances=base
        )
    
    def enrich_level_with_calculations(self, level: PostLevelDetail) -> PostLevelResponse:
        """Add calculated fields to level response"""
        da = self.calculate_dearness_allowance(level.basic_pay, level.grade_pay)
        hra = self.calculate_hra(level.basic_pay, level.grade_pay, level.hra_rate)
        
        total = (
            int(level.special_pay) +
            int(level.basic_pay) +
            int(level.grade_pay) +
            da +
            int(level.local_supplementary_allowance) +
            hra +
            int(level.vehicle_allowance) +
            int(level.washing_allowance) +
            int(level.cash_allowance) +
            int(level.footwear_allowance_other)
        )
        
        response = PostLevelResponse.model_validate(level)
        response.dearness_allowance = da
        response.hra_amount = hra
        response.total = total
        
        return response
    
    def get_levels(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str,
        fiscal_year: str
    ) -> List[PostLevelResponse]:
        """Get all levels with calculated fields"""
        levels = self.repository.get_by_budget_post(budget_post_id, sub_scheme_code, table_name, fiscal_year)
        return [self.enrich_level_with_calculations(level) for level in levels]
    
    def get_level(
        self,
        level_id: int,
        sub_scheme_code: str,
        table_name: str,
        fiscal_year: str
    ) -> Optional[PostLevelResponse]:
        """Get single level with calculated fields"""
        level = self.repository.get_by_id(level_id, sub_scheme_code, table_name, fiscal_year)
        if not level:
            return None
        return self.enrich_level_with_calculations(level)
    
    def create_level(self, data: PostLevelCreate) -> PostLevelResponse:
        """Create new level"""
        level = self.repository.create(data)
        return self.enrich_level_with_calculations(level)
    
    def update_level(
        self,
        level_id: int,
        sub_scheme_code: str,
        table_name: str,
        fiscal_year: str,
        data: PostLevelUpdate
    ) -> Optional[PostLevelResponse]:
        """Update existing level"""
        level = self.repository.update(level_id, sub_scheme_code, table_name, fiscal_year, data)
        if not level:
            return None
        return self.enrich_level_with_calculations(level)
    
    def delete_level(
        self,
        level_id: int,
        sub_scheme_code: str,
        table_name: str,
        fiscal_year: str
    ) -> bool:
        """Delete level"""
        return self.repository.delete(level_id, sub_scheme_code, table_name, fiscal_year)
    
    def calculate_aggregates(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str,
        fiscal_year: str
    ) -> AggregatedTotals:
        """
        Calculate aggregated totals from all levels
        
        Returns sums of all salary components across levels
        """
        levels = self.repository.get_by_budget_post(budget_post_id, sub_scheme_code, table_name, fiscal_year)
        
        if not levels:
            return AggregatedTotals(
                count=0,
                special_pay=0,
                basic_pay=0.0,
                grade_pay=0,
                local_supplementary_allowance=0,
                vehicle_allowance=0,
                washing_allowance=0,
                cash_allowance=0,
                footwear_allowance_other=0,
                dearness_allowance=0,
                hra_total=0,
                grand_total=0
            )
        
        # Sum all components
        total_special = sum(int(l.special_pay) for l in levels)
        total_basic = sum(float(l.basic_pay) for l in levels)
        total_grade = sum(int(l.grade_pay) for l in levels)
        total_local_supp = sum(int(l.local_supplementary_allowance) for l in levels)
        total_vehicle = sum(int(l.vehicle_allowance) for l in levels)
        total_washing = sum(int(l.washing_allowance) for l in levels)
        total_cash = sum(int(l.cash_allowance) for l in levels)
        total_footwear = sum(int(l.footwear_allowance_other) for l in levels)
        
        # Calculate DA and HRA per level, then sum
        total_da = sum(
            self.calculate_dearness_allowance(l.basic_pay, l.grade_pay)
            for l in levels
        )
        total_hra = sum(
            self.calculate_hra(l.basic_pay, l.grade_pay, l.hra_rate)
            for l in levels
        )
        
        grand_total = (
            total_special + int(total_basic) + total_grade + total_da +
            total_local_supp + total_hra + total_vehicle + total_washing +
            total_cash + total_footwear
        )
        
        return AggregatedTotals(
            count=len(levels),
            special_pay=total_special,
            basic_pay=total_basic,
            grade_pay=total_grade,
            local_supplementary_allowance=total_local_supp,
            vehicle_allowance=total_vehicle,
            washing_allowance=total_washing,
            cash_allowance=total_cash,
            footwear_allowance_other=total_footwear,
            dearness_allowance=total_da,
            hra_total=total_hra,
            grand_total=grand_total
        )
    
    def apply_aggregates_to_budget_post(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str,
        budget_post_model,
        fiscal_year: str
    ) -> Dict[str, Any]:
        """
        Calculate aggregates and update the parent BudgetPostDetails record
        
        Returns the updated aggregates
        """
        # Calculate aggregates
        aggregates = self.calculate_aggregates(budget_post_id, sub_scheme_code, table_name, fiscal_year)
        
        # Get the budget post record with strict isolation checks (defense-in-depth)
        budget_post = self.db.query(budget_post_model).filter(
            budget_post_model.id == budget_post_id,
            budget_post_model.fiscal_year == fiscal_year,
            budget_post_model.sub_scheme_code == sub_scheme_code
        ).first()
        
        if not budget_post:
            raise ValueError(f"Budget post {budget_post_id} not found for sub_scheme {sub_scheme_code} and fiscal year {fiscal_year}")
        
        # Update aggregated fields only
        budget_post.special_pay = aggregates.special_pay
        budget_post.basic_pay = aggregates.basic_pay
        budget_post.grade_pay = aggregates.grade_pay
        budget_post.local_supplementary_allowance = aggregates.local_supplementary_allowance
        budget_post.vehicle_allowance = aggregates.vehicle_allowance
        budget_post.washing_allowance = aggregates.washing_allowance
        budget_post.cash_allowance = aggregates.cash_allowance
        budget_post.footwear_allowance_other = aggregates.footwear_allowance_other
        
        # Note: HRA rate in main record becomes meaningless when using levels
        # We could set it to 'X' as default or leave as-is
        
        self.db.commit()
        
        return aggregates.model_dump()

