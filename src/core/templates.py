"""Centralized Jinja2 template configuration with scheme-aware utilities"""
from fastapi.templating import Jinja2Templates
from fastapi import Request
from src.utils_scheme import get_scheme_url

templates = Jinja2Templates(directory="templates")

templates.env.globals["scheme_url"] = get_scheme_url

