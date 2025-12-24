"""Repository for post level details database operations"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from .models import PostLevelDetail
from .schemas import PostLevelCreate, PostLevelUpdate


class PostLevelRepository:
    """Repository for PostLevelDetail CRUD operations with strict isolation"""
    
    def __init__(self, db: Session):
        """Initialize with database session"""
        self.db = db
    
    def get_by_budget_post(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str
    ) -> List[PostLevelDetail]:
        """
        Get all levels for a budget post with strict isolation
        
        Isolation enforced by: table_name + budget_post_id + sub_scheme_code
        """
        return self.db.query(PostLevelDetail).filter(
            and_(
                PostLevelDetail.table_name == table_name,
                PostLevelDetail.budget_post_id == budget_post_id,
                PostLevelDetail.sub_scheme_code == sub_scheme_code
            )
        ).order_by(PostLevelDetail.level_order).all()
    
    def get_by_id(
        self,
        level_id: int,
        sub_scheme_code: str,
        table_name: str
    ) -> Optional[PostLevelDetail]:
        """
        Get level by ID with isolation check
        
        Always verify sub_scheme_code and table_name to prevent cross-contamination
        """
        return self.db.query(PostLevelDetail).filter(
            and_(
                PostLevelDetail.id == level_id,
                PostLevelDetail.sub_scheme_code == sub_scheme_code,
                PostLevelDetail.table_name == table_name
            )
        ).first()
    
    def create(self, data: PostLevelCreate) -> PostLevelDetail:
        """Create new level with uniqueness validation"""
        # Check if level name already exists for this post
        existing = self.db.query(PostLevelDetail).filter(
            and_(
                PostLevelDetail.table_name == data.table_name,
                PostLevelDetail.budget_post_id == data.budget_post_id,
                PostLevelDetail.sub_scheme_code == data.sub_scheme_code,
                PostLevelDetail.level_name == data.level_name
            )
        ).first()
        
        if existing:
            raise ValueError(f"Level name '{data.level_name}' already exists for this post")
        
        # Create new level
        level = PostLevelDetail(**data.model_dump())
        self.db.add(level)
        self.db.commit()
        self.db.refresh(level)
        return level
    
    def update(
        self,
        level_id: int,
        sub_scheme_code: str,
        table_name: str,
        data: PostLevelUpdate
    ) -> Optional[PostLevelDetail]:
        """Update level with ownership validation"""
        level = self.get_by_id(level_id, sub_scheme_code, table_name)
        if not level:
            return None
        
        # Update only non-None fields
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        
        # If updating level_name, check uniqueness
        if 'level_name' in update_data and update_data['level_name'] != level.level_name:
            existing = self.db.query(PostLevelDetail).filter(
                and_(
                    PostLevelDetail.table_name == table_name,
                    PostLevelDetail.budget_post_id == level.budget_post_id,
                    PostLevelDetail.sub_scheme_code == sub_scheme_code,
                    PostLevelDetail.level_name == update_data['level_name'],
                    PostLevelDetail.id != level_id
                )
            ).first()
            
            if existing:
                raise ValueError(f"Level name '{update_data['level_name']}' already exists for this post")
        
        for key, value in update_data.items():
            setattr(level, key, value)
        
        self.db.commit()
        self.db.refresh(level)
        return level
    
    def delete(
        self,
        level_id: int,
        sub_scheme_code: str,
        table_name: str
    ) -> bool:
        """Delete level with ownership validation"""
        level = self.get_by_id(level_id, sub_scheme_code, table_name)
        if not level:
            return False
        
        self.db.delete(level)
        self.db.commit()
        return True
    
    def get_count(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str
    ) -> int:
        """Get count of levels for a budget post"""
        return self.db.query(PostLevelDetail).filter(
            and_(
                PostLevelDetail.table_name == table_name,
                PostLevelDetail.budget_post_id == budget_post_id,
                PostLevelDetail.sub_scheme_code == sub_scheme_code
            )
        ).count()
    
    def reorder_levels(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str,
        level_orders: dict[int, int]
    ) -> None:
        """Update level orders for a budget post"""
        for level_id, new_order in level_orders.items():
            level = self.get_by_id(level_id, sub_scheme_code, table_name)
            if level and level.budget_post_id == budget_post_id:
                level.level_order = new_order
        
        self.db.commit()

