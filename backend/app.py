"""FastAPI app — OTLP HTTP receiver + architecture visualization."""

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.store import store
from backend.otlp import (
    PROTO_CT, JSON_CT,
    decode_traces, decode_metrics, decode_logs,
    encode_trace_response, encode_metrics_response, encode_logs_response,
)

app = FastAPI(title="OTLP HTTP Receiver")


def _content_type(request: Request) -> str:
    ct = request.headers.get("content-type", JSON_CT)
    return PROTO_CT if "protobuf" in ct else JSON_CT


# ── OTLP ingest endpoints ──────────────────────────────────────────

@app.post("/v1/traces")
async def ingest_traces(request: Request):
    body = await request.body()
    ct = _content_type(request)
    resource_spans = decode_traces(body, ct)
    store.add_traces(resource_spans)
    return Response(
        content=encode_trace_response(ct),
        media_type=ct,
    )


@app.post("/v1/metrics")
async def ingest_metrics(request: Request):
    body = await request.body()
    ct = _content_type(request)
    resource_metrics = decode_metrics(body, ct)
    store.add_metrics(resource_metrics)
    return Response(
        content=encode_metrics_response(ct),
        media_type=ct,
    )


@app.post("/v1/logs")
async def ingest_logs(request: Request):
    body = await request.body()
    ct = _content_type(request)
    resource_logs = decode_logs(body, ct)
    store.add_logs(resource_logs)
    return Response(
        content=encode_logs_response(ct),
        media_type=ct,
    )


# ── Viewer API ──────────────────────────────────────────────────────

@app.get("/api/telemetry")
async def get_telemetry(kind: str = "traces", limit: int = 50):
    if kind == "traces":
        items = store.get_traces(limit)
    elif kind == "metrics":
        items = store.get_metrics(limit)
    elif kind == "logs":
        items = store.get_logs(limit)
    else:
        items = []
    return {"kind": kind, "items": items}


@app.get("/api/stats")
async def get_stats():
    return store.get_counts()


@app.post("/api/clear")
async def clear_store():
    store.clear()
    return {"status": "cleared"}


# ── Prometheus proxy (avoids CORS) ──────────────────────────────────

PROMETHEUS_URL = "https://production-prometheus-embr-1a780423.app.embr.azure"

@app.get("/api/prometheus")
async def prometheus_query(query: str = "up"):
    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
        return Response(
            content=resp.content,
            media_type="application/json",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )


# ── Static UI ───────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/viz.html")
async def viz():
    return FileResponse("static/viz.html")


@app.get("/viz2.html")
async def viz2():
    return FileResponse("static/viz2.html")


@app.get("/viz3.html")
async def viz3():
    return FileResponse("static/viz3.html")


@app.get("/arch.html")
async def arch():
    return FileResponse("static/arch.html", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    })
