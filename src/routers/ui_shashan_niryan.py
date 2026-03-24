import mimetypes
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from src.core.templates import render
from src.utils_scheme import get_scheme_base_template

_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "Shashan_Nirnay"

_PDF_CONFIG_RAW = [
    {"file": "Gazette Seventh Pay.pdf",                          "title": "Gazette Seventh Pay"},
    {"file": "Palghar-31-04-14 New Post-102.pdf",                "title": "Palghar-31-04-14 New Post-102"},
    {"file": "Budget Form File P.PDF",                           "title": "Budget Form File P"},
    {"file": "आकृतीबंध शा.नि.20-03-2006.pdf",                    "title": "आकृतीबंध शा.नि.20-03-2006"},
    {"file": "HRA All GR upto 2019 merged.pdf",                  "title": "HRA All GR upto 2019 (Merged GRs)"},
    {"file": "Revised Travelling Allowance Rate 20.04.2022.pdf",  "title": "Revised Travelling Allowance Rate 20.04.2022"},
]

# Pre-compute at module load: URL, mime type, ETag per file. Zero per-request overhead.
def _build_pdf_entries():
    entries = []
    allowed = {}
    for item in _PDF_CONFIG_RAW:
        filename = item["file"]
        path = _DOCS_DIR / filename
        url = "/shashan-nirnay-pdf/" + quote(filename, safe="")
        mime, _ = mimetypes.guess_type(filename)

        etag = None
        last_modified = None
        if path.is_file():
            stat = path.stat()
            etag = f'"{int(stat.st_mtime)}-{stat.st_size}"'
            last_modified = stat.st_mtime

        entries.append({"title": item["title"], "url": url})
        allowed[filename] = {
            "path": path,
            "mime": mime or "application/pdf",
            "etag": etag,
            "last_modified": last_modified,
        }
    return entries, allowed


_PDF_ENTRIES, _ALLOWED_FILES = _build_pdf_entries()

router = APIRouter(tags=["UI - शासन निर्णय"], include_in_schema=False)


@router.get("/ui/s{scheme_code}/shashan-niryan", response_class=HTMLResponse)
async def ui_shashan_niryan(request: Request, scheme_code: str):
    return render(
        request,
        "shashan_niryan.html",
        {
            "resource_name": "शासन निर्णय",
            "auth_level": request.cookies.get("auth_level") or "",
            "pdfs": _PDF_ENTRIES,
            "base_template": get_scheme_base_template(request),
            "scheme_code": scheme_code,
        },
    )


@router.get("/shashan-nirnay-pdf/{filename:path}")
async def serve_shashan_nirnay_pdf(request: Request, filename: str):
    safe_name = unquote(filename)

    meta = _ALLOWED_FILES.get(safe_name)
    if meta is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not meta["path"].is_file():
        raise HTTPException(status_code=404, detail="Document not found.")

    if meta["etag"]:
        if request.headers.get("if-none-match") == meta["etag"]:
            return Response(status_code=304, headers={"ETag": meta["etag"]})

    return FileResponse(
        path=str(meta["path"]),
        media_type=meta["mime"],
        headers={
            "Cache-Control": "public, max-age=86400",
            "ETag": meta["etag"] or "",
        },
    )
