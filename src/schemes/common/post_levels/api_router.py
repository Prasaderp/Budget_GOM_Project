"""API router factory for post level endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Callable, Tuple
from src.database import get_db
from src.utils_fiscal_year import get_fiscal_year_from_request
from src.utils_timing import check_data_filling_allowed
from .service import PostLevelService
from .schemas import (
    PostLevelCreate, PostLevelUpdate, PostLevelResponse,
    PostLevelCalculateRequest, PostLevelCalculateResponse,
    AggregatedTotals
)


def create_post_levels_router(
    sub_scheme_code: str,
    budget_post_model,
    table_name: str,
    scheme_code: str,
    access_validator: Callable[[Request, any, Session], Tuple[bool, str]],
    prefix: str = "/api/post-levels"
) -> APIRouter:
    """
    Factory function to create post levels router for a subscheme
    
    Args:
        sub_scheme_code: The subscheme code (e.g., "20530028")
        budget_post_model: The SQLAlchemy model for budget post details
        table_name: The table name (e.g., "budget_post_details_20530028")
        scheme_code: The scheme code for timing validation (e.g., "2053")
        access_validator: Callback function to validate user access to budget post
        prefix: API prefix (default: "/api/post-levels")
    
    Returns:
        Configured APIRouter with all post level endpoints
    """
    router = APIRouter(prefix=prefix, tags=[f"Post Levels - {sub_scheme_code}"])
    
    def get_service(request: Request, db: Session = Depends(get_db)) -> PostLevelService:
        """Dependency to get post level service with fiscal year context"""
        fiscal_year = get_fiscal_year_from_request(request, db)
        return PostLevelService(db, fiscal_year)
    
    @router.get("/{budget_post_id}", response_model=List[PostLevelResponse])
    async def list_levels(
        request: Request,
        budget_post_id: int,
        service: PostLevelService = Depends(get_service),
        db: Session = Depends(get_db)
    ):
        """Get all levels for a budget post"""
        try:
            # Get fiscal year from request
            fiscal_year = get_fiscal_year_from_request(request, db)
            
            # Verify budget post exists and belongs to current fiscal year
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == budget_post_id,
                budget_post_model.fiscal_year == fiscal_year
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Budget post {budget_post_id} not found for current fiscal year"
                )
            
            # Validate access control
            allowed, error_msg = access_validator(request, budget_post, db)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_msg
                )
            
            levels = service.get_levels(budget_post_id, sub_scheme_code, table_name, fiscal_year)
            return levels
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.post("", response_model=PostLevelResponse, status_code=status.HTTP_201_CREATED)
    async def create_level(
        request: Request,
        level_data: PostLevelCreate,
        service: PostLevelService = Depends(get_service),
        db: Session = Depends(get_db)
    ):
        """Create a new level for a budget post"""
        try:
            # Get fiscal year from request
            fiscal_year = get_fiscal_year_from_request(request, db)
            
            # Get auth credentials
            auth_level = request.cookies.get('auth_level', '')
            auth_role = request.cookies.get('auth_role', '')
            
            # Check timing/permissions
            is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, scheme_code)
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=timing_msg or "Data filling period has expired"
                )
            
            # Verify budget post exists and belongs to current fiscal year
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == level_data.budget_post_id,
                budget_post_model.fiscal_year == fiscal_year
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Budget post {level_data.budget_post_id} not found for current fiscal year"
                )
            
            # Validate access control
            allowed, error_msg = access_validator(request, budget_post, db)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_msg
                )
            
            # Enforce isolation: set the correct values
            level_data.sub_scheme_code = sub_scheme_code
            level_data.table_name = table_name
            level_data.fiscal_year = fiscal_year
            
            # Create level
            level = service.create_level(level_data)
            return level
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.put("/{level_id}", response_model=PostLevelResponse)
    async def update_level(
        request: Request,
        level_id: int,
        level_data: PostLevelUpdate,
        service: PostLevelService = Depends(get_service),
        db: Session = Depends(get_db)
    ):
        """Update an existing level"""
        try:
            # Get fiscal year from request
            fiscal_year = get_fiscal_year_from_request(request, db)
            
            # Get auth credentials
            auth_level = request.cookies.get('auth_level', '')
            auth_role = request.cookies.get('auth_role', '')
            
            # Check timing/permissions
            is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, scheme_code)
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=timing_msg or "Data filling period has expired"
                )
            
            # Get existing level to validate ownership
            existing_level = service.get_level(level_id, sub_scheme_code, table_name, fiscal_year)
            if not existing_level:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Level {level_id} not found for current fiscal year"
                )
            
            # Get budget post for access validation
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == existing_level.budget_post_id,
                budget_post_model.fiscal_year == fiscal_year
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Budget post not found"
                )
            
            # Validate access control
            allowed, error_msg = access_validator(request, budget_post, db)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_msg
                )
            
            # Update level
            level = service.update_level(level_id, sub_scheme_code, table_name, fiscal_year, level_data)
            
            if not level:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Level {level_id} not found"
                )
            
            return level
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.delete("/{level_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_level(
        request: Request,
        level_id: int,
        service: PostLevelService = Depends(get_service),
        db: Session = Depends(get_db)
    ):
        """Delete a level"""
        try:
            # Get fiscal year from request
            fiscal_year = get_fiscal_year_from_request(request, db)
            
            # Get auth credentials
            auth_level = request.cookies.get('auth_level', '')
            auth_role = request.cookies.get('auth_role', '')
            
            # Check timing/permissions
            is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, scheme_code)
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=timing_msg or "Data filling period has expired"
                )
            
            # Get existing level to validate ownership
            existing_level = service.get_level(level_id, sub_scheme_code, table_name, fiscal_year)
            if not existing_level:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Level {level_id} not found for current fiscal year"
                )
            
            # Get budget post for access validation
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == existing_level.budget_post_id,
                budget_post_model.fiscal_year == fiscal_year
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Budget post not found"
                )
            
            # Validate access control
            allowed, error_msg = access_validator(request, budget_post, db)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_msg
                )
            
            # Delete level
            success = service.delete_level(level_id, sub_scheme_code, table_name, fiscal_year)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Level {level_id} not found"
                )
            
            return None
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.post("/calculate", response_model=PostLevelCalculateResponse)
    async def calculate_allowances(
        request: PostLevelCalculateRequest,
        service: PostLevelService = Depends(get_service)
    ):
        """Calculate DA and HRA without saving (for frontend preview)"""
        try:
            return service.calculate_allowances(request)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.get("/{budget_post_id}/aggregates", response_model=AggregatedTotals)
    async def get_aggregates(
        request: Request,
        budget_post_id: int,
        service: PostLevelService = Depends(get_service),
        db: Session = Depends(get_db)
    ):
        """Calculate and return aggregated totals from all levels (preview only)"""
        try:
            # Get fiscal year from request
            fiscal_year = get_fiscal_year_from_request(request, db)
            
            # Verify budget post exists and belongs to current fiscal year
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == budget_post_id,
                budget_post_model.fiscal_year == fiscal_year
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Budget post {budget_post_id} not found for current fiscal year"
                )
            
            aggregates = service.calculate_aggregates(budget_post_id, sub_scheme_code, table_name, fiscal_year)
            return aggregates
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.post("/{budget_post_id}/apply-aggregates", response_model=dict)
    async def apply_aggregates(
        request: Request,
        budget_post_id: int,
        service: PostLevelService = Depends(get_service),
        db: Session = Depends(get_db)
    ):
        """Calculate aggregates and update the parent budget post record"""
        try:
            # Get fiscal year from request
            fiscal_year = get_fiscal_year_from_request(request, db)
            
            # Get auth credentials
            auth_level = request.cookies.get('auth_level', '')
            auth_role = request.cookies.get('auth_role', '')
            
            # Check timing/permissions
            is_allowed, timing_msg = check_data_filling_allowed(db, auth_level, auth_role, scheme_code)
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=timing_msg or "Data filling period has expired"
                )
            
            # Verify budget post exists and belongs to current fiscal year
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == budget_post_id,
                budget_post_model.fiscal_year == fiscal_year
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Budget post {budget_post_id} not found for current fiscal year"
                )
            
            # Validate access control
            allowed, error_msg = access_validator(request, budget_post, db)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_msg
                )
            
            # Apply aggregates
            aggregates = service.apply_aggregates_to_budget_post(
                budget_post_id,
                sub_scheme_code,
                table_name,
                budget_post_model,
                fiscal_year
            )
            
            return {
                "success": True,
                "message": "Aggregates applied successfully",
                "aggregates": aggregates
            }
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    return router
