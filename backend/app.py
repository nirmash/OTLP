"""FastAPI app — OTLP HTTP receiver + viewer UI."""

import logging
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
logger = logging.getLogger("otlp_receiver")
logging.basicConfig(level=logging.INFO)


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
    logger.info("POST /v1/logs ct=%s body_len=%d", ct, len(body))
    resource_logs = decode_logs(body, ct)
    logger.info("decoded %d resource_logs", len(resource_logs))
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


# ── Static UI ───────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")
