"""Response utility functions for HTTP responses and Excel exports."""
import io
import time
from typing import Dict, Optional, Union
from starlette.responses import StreamingResponse


EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def get_no_cache_headers() -> Dict[str, str]:
    """Get standard no-cache headers for responses."""
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }


def create_excel_response(
    content: Union[io.BytesIO, bytes],
    base_filename: str,
    fiscal_year: Optional[str] = None,
    include_timestamp: bool = True
) -> StreamingResponse:
    """Create a cache-safe StreamingResponse for Excel file downloads."""
    filename_parts = [base_filename]

    if fiscal_year:
        safe_fy = fiscal_year.replace("/", "-").replace("\\", "-")
        filename_parts.append(safe_fy)

    if include_timestamp:
        filename_parts.append(str(int(time.time())))

    filename = "_".join(filename_parts) + ".xlsx"

    headers = get_no_cache_headers()
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    if isinstance(content, io.BytesIO):
        content.seek(0)

    return StreamingResponse(content=content, headers=headers, media_type=EXCEL_MEDIA_TYPE)
