import logging
import mimetypes
import re
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response

from src.core.registry import scheme_registry
from src.core.templates import render
from src.utils_auth import get_auth_level, get_auth_role, get_auth_user, is_authenticated
from src.utils_scheme import get_scheme_base_template

logger = logging.getLogger(__name__)

_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "Shashan_Nirnay"

_PDF_CONFIG_RAW: list[dict[str, str]] = [
    {"file": "Gazette Seventh Pay.pdf",                         "title": "Gazette Seventh Pay"},
    {"file": "Palghar-31-04-14 New Post-102.pdf",               "title": "Palghar-31-04-14 New Post-102"},
    {"file": "Budget Form File P.PDF",                          "title": "Budget Form File P"},
    {"file": "आकृतीबंध शा.नि.20-03-2006.pdf",                   "title": "आकृतीबंध शा.नि.20-03-2006"},
    {"file": "HRA All GR upto 2019 merged.pdf",                 "title": "HRA All GR upto 2019 (Merged GRs)"},
    {"file": "Revised Travelling Allowance Rate 20.04.2022.pdf", "title": "Revised Travelling Allowance Rate 20.04.2022"},
]

_SCHEME_CODE_RE = re.compile(r"^[0-9]{4,8}$")


def _build_pdf_entries() -> tuple[list[dict], dict]:
    entries: list[dict] = []
    allowed: dict[str, dict] = {}
    for item in _PDF_CONFIG_RAW:
        filename = item["file"]
        path = _DOCS_DIR / filename
        url = "/shashan-nirnay-pdf/" + quote(filename, safe="")
        mime, _ = mimetypes.guess_type(filename)

        etag: str | None = None
        if path.is_file():
            stat = path.stat()
            etag = f'"{int(stat.st_mtime)}-{stat.st_size}"'
        else:
            logger.warning("shashan_nirnay pdf_missing file=%s", filename)

        entries.append({"title": item["title"], "url": url})
        allowed[filename] = {
            "path": path,
            "mime": mime or "application/pdf",
            "etag": etag,
        }
    return entries, allowed


_PDF_ENTRIES, _ALLOWED_FILES = _build_pdf_entries()

router = APIRouter(
    prefix="/ui/s{scheme_code}/shashan-niryan",
    tags=["UI - शासन निर्णय"],
    include_in_schema=False,
)

_PDF_ROUTER = APIRouter(tags=["UI - शासन निर्णय"], include_in_schema=False)


def _validate_scheme(scheme_code: str) -> None:
    if not _SCHEME_CODE_RE.match(scheme_code):
        raise HTTPException(status_code=400, detail="Invalid scheme code")
    if not scheme_registry.get_scheme(scheme_code):
        raise HTTPException(status_code=404, detail="Scheme not found")


def _require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("", response_class=HTMLResponse)
async def ui_shashan_niryan(request: Request, scheme_code: str) -> HTMLResponse:
    _require_auth(request)
    _validate_scheme(scheme_code)
    return render(
        request,
        "shashan_niryan.html",
        {
            "resource_name": "शासन निर्णय",
            "auth_level": get_auth_level(request),
            "auth_role": get_auth_role(request),
            "auth_user": get_auth_user(request),
            "pdfs": _PDF_ENTRIES,
            "base_template": get_scheme_base_template(request),
            "scheme_code": scheme_code,
        },
    )


@_PDF_ROUTER.get("/shashan-nirnay-pdf/{filename:path}")
async def serve_shashan_nirnay_pdf(request: Request, filename: str) -> Response:
    safe_name = unquote(filename)

    if ".." in safe_name or safe_name.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    meta = _ALLOWED_FILES.get(safe_name)
    if meta is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not meta["path"].is_file():
        logger.error("shashan_nirnay pdf_serve_missing file=%s", safe_name)
        raise HTTPException(status_code=404, detail="Document not found")

    if meta["etag"] and request.headers.get("if-none-match") == meta["etag"]:
        return Response(status_code=304, headers={"ETag": meta["etag"]})

    headers: dict[str, str] = {"Cache-Control": "public, max-age=86400"}
    if meta["etag"]:
        headers["ETag"] = meta["etag"]

    return FileResponse(
        path=str(meta["path"]),
        media_type=meta["mime"],
        headers=headers,
    )
