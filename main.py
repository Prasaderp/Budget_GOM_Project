import sys
import os
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
from database import engine, SessionLocal, get_db

from routers import ui_budget_details, ui_post_status, ui_post_expenses, ui_unit_expenditure, ui_abstract, ui_category_info, ui_budget_summary # Ensure ui_budget_summary is imported
from routers import api_assistant

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

models.Base.metadata.create_all(bind=engine)

app.include_router(ui_budget_details.router)
app.include_router(ui_post_status.router)
app.include_router(ui_post_expenses.router)
app.include_router(ui_unit_expenditure.router)
app.include_router(ui_abstract.router)
app.include_router(ui_category_info.router)
app.include_router(ui_budget_summary.router) # Ensure ui_budget_summary is included
app.include_router(api_assistant.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})