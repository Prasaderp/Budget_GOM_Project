from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from src.core.templates import templates
from src.utils_scheme import get_scheme_base_template

PDF_CONFIG = [
    {
        "file": "Gazette Seventh Pay.pdf",
        "title": "Gazette Seventh Pay",
        "sub_title": "",
    },
    {
        "file": "Palghar-31-04-14 New Post-102.pdf",
        "title": "Palghar-31-04-14 New Post-102",
        "sub_title": "",
    },
    {
        "file": "Budget Form File P.PDF",
        "title": "Budget Form File P",
        "sub_title": "",
    },
    {
        "file": "आकृतीबंध शा.नि.20-03-2006.pdf",
        "title": "आकृतीबंध शा.नि.20-03-2006",
        "sub_title": "",
    },
    {
        "file": "HRA All GR upto 2019 merged.pdf",
        "title": "HRA All GR upto 2019 (Merged GRs)",
        "sub_title": "",
    },
    {
        "file": "Revised Travelling Allowance Rate 20.04.2022.pdf",
        "title": "Revised Travelling Allowance Rate 20.04.2022",
        "sub_title": "",
    },
]

router = APIRouter(
    prefix="/ui/s{scheme_code}/shashan-niryan",
    tags=["UI - शासन निर्णय"],
    include_in_schema=False
)

@router.get("", response_class=HTMLResponse)
async def ui_shashan_niryan(request: Request, scheme_code: str):
    return templates.TemplateResponse(
        "shashan_niryan.html",
        {
            "request": request,
            "resource_name": "शासन निर्णय",
            "auth_level": request.cookies.get("auth_level") or "",
            "pdfs": PDF_CONFIG,
            "base_template": get_scheme_base_template(request),
            "scheme_code": scheme_code,
        },
    )

