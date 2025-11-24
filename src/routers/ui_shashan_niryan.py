from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.database import get_db

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ui/shashan-niryan",
    tags=["UI - शासन निर्याण"],
    include_in_schema=False
)

@router.get("", response_class=HTMLResponse)
async def ui_shashan_niryan(request: Request, db: Session = Depends(get_db)):
    auth_level = request.cookies.get('auth_level') or ''
    
    response = templates.TemplateResponse("shashan_niryan.html", {
        "request": request,
        "resource_name": "शासन निर्याण",
        "auth_level": auth_level
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

