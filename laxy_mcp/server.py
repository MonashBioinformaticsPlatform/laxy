#!/usr/bin/env python
"""Laxy MCP sidecar spike — mcp 2.0 SDK over the REST API.

Relays the inbound Authorization bearer token to Django so existing
permissions apply. Comparison spike against the in-Django endpoint.
"""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar
from typing import Any

import httpx
from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("laxy_mcp")

LAXY_API_BASE = os.environ.get("LAXY_API_BASE_URL", "http://django:8001/api/v1").rstrip(
    "/"
)
PORT = int(os.environ.get("LAXY_MCP_PORT", "8003"))

_auth_header: ContextVar[str | None] = ContextVar("laxy_auth_header", default=None)

READ_ONLY = ToolAnnotations(readOnlyHint=True)

server = MCPServer(
    name="laxy-sidecar",
    version="0.1.0",
    instructions="Laxy MCP sidecar (REST-backed spike).",
)


def _headers() -> dict[str, str]:
    auth = _auth_header.get()
    if not auth:
        raise PermissionError("Authorization Bearer token required")
    # MCP clients send Bearer; Laxy DRF tokens expect the Token scheme.
    # JWTs keep Bearer. Try Token scheme for non-JWT-looking credentials.
    parts = auth.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        if token.count(".") != 2:
            auth = f"Token {token}"
    return {
        "Authorization": auth,
        "Accept": "application/json",
        "X-Forwarded-Proto": "https",
    }


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{LAXY_API_BASE}/{path.lstrip('/')}"
    with httpx.Client(timeout=60.0, verify=False, follow_redirects=True) as client:
        resp = client.get(url, headers=_headers(), params=params or {})
        resp.raise_for_status()
        return resp.json()


@server.tool(
    name="laxy_list_jobs",
    description="List jobs for the authenticated user via the Laxy REST API.",
    annotations=READ_ONLY,
)
def laxy_list_jobs(
    ctx: Context,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    data = _get("jobs/")
    jobs = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        jobs = []
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    return jobs[: max(1, min(int(limit), 100))]


@server.tool(
    name="laxy_get_job_eventlogs",
    description="List event logs for a job via GET /eventlogs/?object_id=...",
    annotations=READ_ONLY,
)
def laxy_get_job_eventlogs(
    ctx: Context,
    job_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    data = _get("eventlogs/", params={"object_id": job_id})
    events = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(events, list):
        events = []
    return events[: max(1, min(int(limit), 200))]


class CaptureAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("authorization")
        token = _auth_header.set(auth)
        try:
            return await call_next(request)
        finally:
            _auth_header.reset(token)


app = server.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
)
app.add_middleware(CaptureAuthMiddleware)

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Laxy MCP sidecar on :%s -> %s", PORT, LAXY_API_BASE)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
