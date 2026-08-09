"""Local, non-mutating smoke check for the Vercel FastAPI entrypoint."""

import asyncio

import httpx
from fastapi import FastAPI

from app.main import app


async def run() -> None:
    assert isinstance(app, FastAPI), f"Expected FastAPI app, got {type(app)!r}"
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/" in paths
    assert "/health" in paths

    openapi = app.openapi()
    assert openapi["openapi"].startswith("3.")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://smoke.test") as client:
        root = await client.get("/")
        health = await client.get("/health")
        docs = await client.get("/docs")
        openapi_response = await client.get("/openapi.json")
    assert root.status_code == 200 and root.json()["service"] == "PermitOps API"
    assert health.status_code == 200 and health.json()["status"] == "ok"
    assert docs.status_code == 200 and "Swagger UI" in docs.text
    assert openapi_response.status_code == 200 and openapi_response.json()["openapi"].startswith("3.")
    print("Vercel FastAPI backend smoke: PASS")


if __name__ == "__main__":
    asyncio.run(run())
