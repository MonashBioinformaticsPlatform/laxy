# Laxy MCP sidecar spike (not deployed)

Experimental MCP 2.0 server that proxies to the Laxy REST API.
The **supported** MCP endpoint is in-Django at `/api/v1/mcp/`
(see `laxy_backend/mcp.py`).

This package was built during the architecture spike for comparison:

| Criterion | In-Django (`django-stateless-mcp`) | This sidecar |
|-----------|-------------------------------------|--------------|
| Protocol | MCP 2.0 GA (`mcp==2.0.0`) | MCP 2.0 GA |
| Extra service | No | Yes (image + network + auth relay) |
| Auth | DRF JWT / Token via `LaxyTokenVerifier` | Relay Bearer → REST |
| Event logs | One ORM query | REST round-trip (+ pagination) |
| Gevent | Works with `DJANGO_ALLOW_ASYNC_UNSAFE` in auth path; prefer `gthread` for MCP workers | N/A (uvicorn) |
| Deps in Django image | `mcp`, `django-stateless-mcp`, `jsonschema>=4.20` | None |

**Decision:** ship the in-Django endpoint. Keep this spike for reference; it is not wired into `docker-compose*.yml`.

```bash
docker build -f docker/laxy-mcp/Dockerfile -t laxy-mcp:spike .
docker run --rm --network laxy_default -p 8003:8003 \
  -e LAXY_API_BASE_URL=http://django:8001/api/v1 laxy-mcp:spike
```
