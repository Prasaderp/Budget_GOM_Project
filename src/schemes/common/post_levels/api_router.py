"""API router factory for post level endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
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
    prefix: str = "/api/post-levels"
) -> APIRouter:
    """
    Factory function to create post levels router for a subscheme
    
    Args:
        sub_scheme_code: The subscheme code (e.g., "20530028")
        budget_post_model: The SQLAlchemy model for budget post details
        table_name: The table name (e.g., "budget_post_details_20530028")
        prefix: API prefix (default: "/api/post-levels")
    
    Returns:
        Configured APIRouter with all post level endpoints
    """
    router = APIRouter(prefix=prefix, tags=[f"Post Levels - {sub_scheme_code}"])
    
    def get_service(db: Session = Depends(get_db)) -> PostLevelService:
        """Dependency to get post level service"""
        return PostLevelService(db)
    
    @router.get("/{budget_post_id}", response_model=List[PostLevelResponse])
    async def list_levels(
        budget_post_id: int,
        service: PostLevelService = Depends(get_service)
    ):
        """Get all levels for a budget post"""
        try:
            # Verify budget post exists
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == budget_post_id
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Budget post {budget_post_id} not found"
                )
            
            levels = service.get_levels(budget_post_id, sub_scheme_code, table_name)
            return levels
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.post("", response_model=PostLevelResponse, status_code=status.HTTP_201_CREATED)
    async def create_level(
        level_data: PostLevelCreate,
        service: PostLevelService = Depends(get_service)
    ):
        """Create a new level for a budget post"""
        try:
            # Verify budget post exists and belongs to this subscheme
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == level_data.budget_post_id
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Budget post {level_data.budget_post_id} not found"
                )
            
            # Enforce isolation: set the correct values
            level_data.sub_scheme_code = sub_scheme_code
            level_data.table_name = table_name
            level_data.fiscal_year = budget_post.fiscal_year
            
            # Create level
            level = service.create_level(level_data)
            return level
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
        level_id: int,
        level_data: PostLevelUpdate,
        service: PostLevelService = Depends(get_service)
    ):
        """Update an existing level"""
        try:
            level = service.update_level(level_id, sub_scheme_code, table_name, level_data)
            
            if not level:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Level {level_id} not found"
                )
            
            return level
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
        level_id: int,
        service: PostLevelService = Depends(get_service)
    ):
        """Delete a level"""
        try:
            success = service.delete_level(level_id, sub_scheme_code, table_name)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Level {level_id} not found"
                )
            
            return None
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
        budget_post_id: int,
        service: PostLevelService = Depends(get_service)
    ):
        """Calculate and return aggregated totals from all levels (preview only)"""
        try:
            aggregates = service.calculate_aggregates(budget_post_id, sub_scheme_code, table_name)
            return aggregates
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.post("/{budget_post_id}/apply-aggregates", response_model=dict)
    async def apply_aggregates(
        budget_post_id: int,
        service: PostLevelService = Depends(get_service)
    ):
        """Calculate aggregates and update the parent budget post record"""
        try:
            # Verify budget post exists
            budget_post = service.db.query(budget_post_model).filter(
                budget_post_model.id == budget_post_id
            ).first()
            
            if not budget_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Budget post {budget_post_id} not found"
                )
            
            # Apply aggregates
            aggregates = service.apply_aggregates_to_budget_post(
                budget_post_id,
                sub_scheme_code,
                table_name,
                budget_post_model
            )
            
            return {
                "success": True,
                "message": "Aggregates applied successfully",
                "aggregates": aggregates
            }
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

