from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from src.utils_scheme import get_scheme_url

templates = Jinja2Templates(directory="templates")
templates.env.globals["scheme_url"] = get_scheme_url


def render(request: Request, name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    ctx = {k: v for k, v in context.items() if k != "request"}
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
