"""Redirect UI updates back to the exact resource path that was submitted.

Taluka write resolution may return an editable row whose ID differs from the ID
in the request path. Building this redirect from that row would send district
users to an office-contribution row their read scope cannot access.
"""

from urllib.parse import urlencode

from fastapi import Request, status
from fastapi.responses import RedirectResponse

_SAVED_MARKER = "saved"


def redirect_after_update(request: Request) -> RedirectResponse:
    """Return a PRG redirect to the submitted route with a one-shot save marker."""
    path = request.url.path
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("UI update redirects require a local absolute path")

    query = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key != _SAVED_MARKER
    ]
    query.append((_SAVED_MARKER, "1"))
    return RedirectResponse(
        url=f"{path}?{urlencode(query)}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
