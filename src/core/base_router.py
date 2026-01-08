"""Base router factory for scheme-specific routes"""
from typing import Type, Optional, List, Callable, Any
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from .base_config import BaseSchemeConfig
from .registry import scheme_registry

class SchemeRouterFactory:
    """Factory for creating scheme-specific routers"""
    
    def __init__(self, config: BaseSchemeConfig, templates_dir: str = "templates"):
        self.config = config
        self.templates = Jinja2Templates(directory=templates_dir)
        self.api_router = APIRouter(
            prefix=f"/api/schemes/{config.code}",
            tags=[f"API - {config.name_mr}"]
        )
        self.ui_router = APIRouter(
            prefix=f"/ui/schemes/{config.code}",
            tags=[f"UI - {config.name_mr}"],
            include_in_schema=False
        )
    
    def get_template_path(self, template_name: str) -> str:
        """Get template path with fallback logic"""
        return scheme_registry.get_template_path(self.config.code, template_name)
    
    def create_list_endpoint(
        self,
        model_class: Type,
        template_name: str,
        resource_name: str
    ) -> Callable:
        """Create a generic list endpoint"""
        config = self.config
        templates = self.templates
        
        async def list_endpoint(
            request: Request,
            db: Session = Depends(get_db),
            page: int = Query(1, ge=1),
            page_size: int = Query(50, ge=1, le=500)
        ):
            from src.utils_fiscal_year import get_fiscal_year_from_request
            
            fiscal_year = get_fiscal_year_from_request(request, db)
            
            query = db.query(model_class).filter(
                model_class.fiscal_year == fiscal_year,
                model_class.sub_scheme_code == config.code
            )
            
            total_count = query.with_entities(func.count()).scalar()
            items = query.order_by(model_class.id).offset((page - 1) * page_size).limit(page_size).all()
            
            template_path = self.get_template_path(template_name)
            
            return templates.TemplateResponse(template_path, {
                "request": request,
                "resource_name": resource_name,
                "items": items,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "scheme_config": config
            })
        
        return list_endpoint
    
    def create_crud_endpoints(
        self,
        model_class: Type,
        schema_create: Type,
        schema_update: Type,
        schema_response: Type
    ) -> None:
        """Create standard CRUD API endpoints"""
        config = self.config
        
        @self.api_router.get("/", response_model=List[schema_response])
        async def list_items(
            skip: int = 0,
            limit: int = 100,
            fiscal_year: Optional[str] = None,
            db: Session = Depends(get_db)
        ):
            from src.utils_fiscal_year import validate_fiscal_year
            validated_fy = validate_fiscal_year(fiscal_year, db)
            return db.query(model_class).filter(
                model_class.fiscal_year == validated_fy,
                model_class.sub_scheme_code == config.code
            ).offset(skip).limit(limit).all()
        
        @self.api_router.get("/{id}", response_model=schema_response)
        async def get_item(id: int, db: Session = Depends(get_db)):
            item = db.query(model_class).filter(
                model_class.id == id,
                model_class.sub_scheme_code == config.code
            ).first()
            if not item:
                raise HTTPException(status_code=404, detail="Record not found")
            return item
        
        @self.api_router.post("/", response_model=schema_response, status_code=201)
        async def create_item(data: schema_create, db: Session = Depends(get_db)):
            from src.utils_fiscal_year import validate_fiscal_year
            item_data = data.model_dump()
            item_data['fiscal_year'] = validate_fiscal_year(item_data.get('fiscal_year'), db)
            item_data['scheme_code'] = config.parent_scheme
            item_data['sub_scheme_code'] = config.code
            db_item = model_class(**item_data)
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item
        
        @self.api_router.put("/{id}", response_model=schema_response)
        async def update_item(id: int, data: schema_update, db: Session = Depends(get_db)):
            db_item = db.query(model_class).filter(
                model_class.id == id,
                model_class.sub_scheme_code == config.code
            ).first()
            if not db_item:
                raise HTTPException(status_code=404, detail="Record not found")
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_item, key, value)
            db.commit()
            db.refresh(db_item)
            return db_item
        
        @self.api_router.delete("/{id}", status_code=204)
        async def delete_item(id: int, db: Session = Depends(get_db)):
            db_item = db.query(model_class).filter(
                model_class.id == id,
                model_class.sub_scheme_code == config.code
            ).first()
            if not db_item:
                raise HTTPException(status_code=404, detail="Record not found")
            db.delete(db_item)
            db.commit()
    
    def get_routers(self) -> tuple:
        """Return both API and UI routers"""
        return self.api_router, self.ui_router

def create_scheme_routers(config: BaseSchemeConfig) -> tuple:
    """Convenience function to create routers for a scheme"""
    factory = SchemeRouterFactory(config)
    return factory.get_routers()

