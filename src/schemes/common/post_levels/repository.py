"""Repository for post level details database operations"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from .models import PostLevelDetail
from .schemas import PostLevelCreate, PostLevelUpdate


class PostLevelRepository:
    """Repository for PostLevelDetail CRUD operations with strict isolation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_budget_post(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str
    ) -> List[PostLevelDetail]:
        """Get all levels for a budget post"""
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
        """Get level by ID with isolation check"""
        return self.db.query(PostLevelDetail).filter(
            and_(
                PostLevelDetail.id == level_id,
                PostLevelDetail.sub_scheme_code == sub_scheme_code,
                PostLevelDetail.table_name == table_name
            )
        ).first()
    
    def get_next_level_order(
        self,
        budget_post_id: int,
        sub_scheme_code: str,
        table_name: str
    ) -> int:
        """Get next available level_order for a budget post"""
        max_order = self.db.query(func.max(PostLevelDetail.level_order)).filter(
            and_(
                PostLevelDetail.table_name == table_name,
                PostLevelDetail.budget_post_id == budget_post_id,
                PostLevelDetail.sub_scheme_code == sub_scheme_code
            )
        ).scalar()
        return (max_order or 0) + 1
    
    def create(self, data: PostLevelCreate) -> PostLevelDetail:
        """Create new level with uniqueness validation"""
        # Check if level name already exists for this post
        existing_name = self.db.query(PostLevelDetail).filter(
            and_(
                PostLevelDetail.table_name == data.table_name,
                PostLevelDetail.budget_post_id == data.budget_post_id,
                PostLevelDetail.sub_scheme_code == data.sub_scheme_code,
                PostLevelDetail.level_name == data.level_name
            )
        ).first()
        
        if existing_name:
            raise ValueError(f"स्तराचे नाव '{data.level_name}' आधीच अस्तित्वात आहे")
        
        # Auto-assign next level_order if not unique or default
        next_order = self.get_next_level_order(
            data.budget_post_id, data.sub_scheme_code, data.table_name
        )
        
        level_data = data.model_dump()
        level_data['level_order'] = next_order  # Always use next available
        
        level = PostLevelDetail(**level_data)
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
                raise ValueError(f"स्तराचे नाव '{update_data['level_name']}' आधीच अस्तित्वात आहे")
        
        # Don't allow changing level_order during update (maintain auto-assigned order)
        update_data.pop('level_order', None)
        
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
        """Delete level"""
        level = self.get_by_id(level_id, sub_scheme_code, table_name)
        if not level:
            return False
        
        budget_post_id = level.budget_post_id
        deleted_order = level.level_order
        
        self.db.delete(level)
        self.db.commit()
        
        # Reorder remaining levels to fill gap
        remaining = self.db.query(PostLevelDetail).filter(
            and_(
                PostLevelDetail.table_name == table_name,
                PostLevelDetail.budget_post_id == budget_post_id,
                PostLevelDetail.sub_scheme_code == sub_scheme_code,
                PostLevelDetail.level_order > deleted_order
            )
        ).all()
        
        for lvl in remaining:
            lvl.level_order -= 1
        
        if remaining:
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
