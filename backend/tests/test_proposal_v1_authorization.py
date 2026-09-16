from backend.app.api.proposal_editor_routers import router as editor_router
from backend.app.api.proposal_source_routers import router as source_router


def _dependency_names(route):
    names = []
    def walk(node):
        for child in node.dependencies:
            names.append(getattr(child.call, "__name__", ""))
            walk(child)
    walk(route.dependant)
    return names


def test_editor_routes_have_role_gate_including_canonical_persistence():
    routes = [route for route in editor_router.routes if getattr(route, "path", "").startswith("/api") or getattr(route, "path", "").startswith("/")]
    assert routes
    assert all("dependency" in _dependency_names(route) for route in routes)


def test_source_create_route_is_present_and_role_gated():
    route = next(route for route in source_router.routes if route.path.endswith("/create-proposal"))
    assert "dependency" in _dependency_names(route)
