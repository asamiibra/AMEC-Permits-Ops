from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute

from backend.app.api.dependencies import current_principal
from backend.app.main import app


PUBLIC_EXACT_PATHS = {
    "/",
    "/health",
}

PUBLIC_PREFIXES = (
    "/mock-authority",
)


def _dependency_tree_contains(
    dependant,
    target,
) -> bool:
    if dependant.call is target:
        return True

    return any(
        _dependency_tree_contains(
            child,
            target,
        )
        for child in dependant.dependencies
    )


def _route_requires_principal(
    route: APIRoute,
) -> bool:
    return _dependency_tree_contains(
        route.dependant,
        current_principal,
    )


def _http_routes(
    application: FastAPI = app,
) -> list[APIRoute]:
    return [
        route
        for route in application.routes
        if isinstance(route, APIRoute)
    ]


def _api_routes(
    application: FastAPI = app,
) -> list[APIRoute]:
    return [
        route
        for route in _http_routes(application)
        if route.path == "/api"
        or route.path.startswith("/api/")
    ]


def _route_by_path(
    path: str,
    application: FastAPI = app,
) -> APIRoute:
    matches = [
        route
        for route in _http_routes(application)
        if route.path == path
    ]

    assert len(matches) == 1, (
        f"Expected exactly one route for {path}; "
        f"found {len(matches)}"
    )

    return matches[0]


def _is_explicitly_public(
    path: str,
) -> bool:
    if path in PUBLIC_EXACT_PATHS:
        return True

    return any(
        path == prefix
        or path.startswith(f"{prefix}/")
        for prefix in PUBLIC_PREFIXES
    )


def _route_label(
    route: APIRoute,
) -> str:
    methods = ",".join(
        sorted(route.methods or set())
    )

    return f"{methods} {route.path}"


def test_http_route_inventory_is_non_empty():
    assert _http_routes()


def test_api_route_inventory_is_non_empty():
    assert _api_routes()


def test_every_api_route_requires_current_principal():
    unprotected = sorted(
        _route_label(route)
        for route in _api_routes()
        if not _route_requires_principal(route)
    )

    assert not unprotected, (
        "Unauthenticated /api routes detected: "
        + "; ".join(unprotected)
    )


def test_every_nonpublic_application_route_is_guarded():
    unprotected = sorted(
        _route_label(route)
        for route in _http_routes()
        if not _is_explicitly_public(route.path)
        and not _route_requires_principal(route)
    )

    assert not unprotected, (
        "Application routes outside the explicit public "
        "allowlist are missing current_principal: "
        + "; ".join(unprotected)
    )


def test_office_route_is_guarded():
    assert _route_requires_principal(
        _route_by_path("/api/office")
    )


def test_dashboard_route_is_guarded():
    assert _route_requires_principal(
        _route_by_path("/api/dashboard")
    )


def test_adapter_health_route_is_guarded():
    assert _route_requires_principal(
        _route_by_path("/api/adapters/health")
    )


def test_health_route_remains_public():
    route = _route_by_path("/health")

    assert _is_explicitly_public(route.path)
    assert not _route_requires_principal(route)


def test_root_route_remains_public():
    route = _route_by_path("/")

    assert _is_explicitly_public(route.path)
    assert not _route_requires_principal(route)


def test_dependency_detector_handles_direct_nested_and_open_routes():
    synthetic_app = FastAPI()

    def nested_dependency(
        principal=Depends(current_principal),
    ):
        return principal

    @synthetic_app.get(
        "/api/direct",
        dependencies=[
            Depends(current_principal),
        ],
    )
    def direct():
        return {"ok": True}

    @synthetic_app.get(
        "/api/nested",
        dependencies=[
            Depends(nested_dependency),
        ],
    )
    def nested():
        return {"ok": True}

    @synthetic_app.get("/api/open")
    def open_route():
        return {"ok": True}

    direct_route = _route_by_path(
        "/api/direct",
        synthetic_app,
    )
    nested_route = _route_by_path(
        "/api/nested",
        synthetic_app,
    )
    open_api_route = _route_by_path(
        "/api/open",
        synthetic_app,
    )

    assert _route_requires_principal(
        direct_route
    )
    assert _route_requires_principal(
        nested_route
    )
    assert not _route_requires_principal(
        open_api_route
    )
