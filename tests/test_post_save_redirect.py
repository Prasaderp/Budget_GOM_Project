import ast
import inspect
import os
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.responses import HTMLResponse

os.environ.setdefault("RUN_DB_CREATE_ALL", "false")

from src.core import templates as template_module
from src.core.ui_redirects import redirect_after_update
from src.schemes.common.excel_export import get_no_cache_headers


ROOT = Path(__file__).resolve().parents[1]
SCHEMES_ROOT = ROOT / "src" / "schemes"
EDIT_ROUTE_SUFFIX = "/{id}/edit"


def make_request(path: str, query: bytes = b"") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "server": ("testserver", 443),
            "path": path,
            "raw_path": path.encode(),
            "query_string": query,
            "headers": [],
        }
    )


def mounted_edit_routes(method: str):
    from src.main import app

    return [
        route
        for route in app.routes
        if method in getattr(route, "methods", set())
        and getattr(route, "path", "").endswith(EDIT_ROUTE_SUFFIX)
    ]


def is_post_edit_decorator(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "post"
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == EDIT_ROUTE_SUFFIX
    )


def source_edit_handlers():
    for path in SCHEMES_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and any(
                is_post_edit_decorator(decorator)
                for decorator in node.decorator_list
            ):
                yield path, tree, node


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def test_every_mounted_update_has_an_identical_get_twin():
    posts = mounted_edit_routes("POST")
    get_paths = {route.path for route in mounted_edit_routes("GET")}

    assert len(posts) == 75
    assert all(route.path in get_paths for route in posts)


def test_every_mounted_update_exposes_request_to_the_redirect_helper():
    posts = mounted_edit_routes("POST")

    assert len(posts) == 75
    assert all(
        "request" in inspect.signature(route.endpoint).parameters for route in posts
    )


def test_every_source_update_uses_the_shared_redirect_after_commit():
    handlers = list(source_edit_handlers())

    assert handlers
    for path, tree, handler in handlers:
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "src.core.ui_redirects"
            for alias in node.names
        }
        calls = [node for node in ast.walk(handler) if isinstance(node, ast.Call)]
        redirect_calls = [
            call for call in calls if call_name(call) == "redirect_after_update"
        ]
        legacy_calls = [
            call for call in calls if call_name(call) == "RedirectResponse"
        ]
        commit_lines = [call.lineno for call in calls if call_name(call) == "commit"]

        location = f"{path.relative_to(ROOT)}:{handler.lineno}"
        assert "redirect_after_update" in imports, location
        assert not legacy_calls, location
        assert len(redirect_calls) == 1, location
        redirect_call = redirect_calls[0]
        assert not redirect_call.keywords, location
        assert len(redirect_call.args) == 1, location
        assert isinstance(redirect_call.args[0], ast.Name), location
        assert redirect_call.args[0].id == "request", location
        assert commit_lines and max(commit_lines) < redirect_call.lineno, location


def test_redirect_uses_the_request_id_not_the_resolved_row_id():
    """Using db_item.id would 404 for district callers after taluka write lifting."""
    response = redirect_after_update(
        make_request(
            "/ui/s20530028/post-expenses/7/edit",
            b"view=edit&tag=one&tag=two&saved=0",
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/ui/s20530028/post-expenses/7/edit"
        "?view=edit&tag=one&tag=two&saved=1"
    )


def test_redirect_api_cannot_accept_an_external_destination():
    assert list(inspect.signature(redirect_after_update).parameters) == ["request"]

    response = redirect_after_update(
        make_request(
            "/ui/s20530028/post-expenses/7/edit",
            b"next=https%3A%2F%2Fevil.example&return_to=%2F%2Fevil.example",
        )
    )
    location = response.headers["location"]
    assert location.startswith("/") and not location.startswith("//")

    with pytest.raises(ValueError, match="local absolute path"):
        redirect_after_update(make_request("//evil.example/edit"))


def test_render_applies_the_shared_private_no_store_policy(monkeypatch):
    monkeypatch.setattr(
        template_module.templates,
        "TemplateResponse",
        lambda request, name, context, status_code: HTMLResponse(
            "rendered", status_code=status_code
        ),
    )

    response = template_module.render(make_request("/ui/page"), "ignored.html", {}, 202)

    assert response.status_code == 202
    for header, value in get_no_cache_headers().items():
        assert response.headers[header] == value


def test_render_cache_policy_survives_application_middleware():
    from src.main import app

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == (
        "no-cache, no-store, must-revalidate, private"
    )


def test_base_template_consumes_and_removes_the_save_marker_once():
    source = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")

    assert "url.searchParams.get('saved') !== '1'" in source
    assert "url.searchParams.delete('saved')" in source
    assert "history.replaceState" in source
    assert "रेकॉर्ड यशस्वीरित्या अपडेट झाला" in source
