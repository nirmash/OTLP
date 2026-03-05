"""Decode OTLP protobuf or JSON payloads into Python dicts."""

from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)

PROTO_CT = "application/x-protobuf"
JSON_CT = "application/json"


def decode_traces(body: bytes, content_type: str) -> list[dict]:
    if content_type == PROTO_CT:
        req = ExportTraceServiceRequest()
        req.ParseFromString(body)
        d = MessageToDict(req, preserving_proto_field_name=True)
    else:
        import json
        d = json.loads(body)
    return d.get("resource_spans", d.get("resourceSpans", []))


def decode_metrics(body: bytes, content_type: str) -> list[dict]:
    if content_type == PROTO_CT:
        req = ExportMetricsServiceRequest()
        req.ParseFromString(body)
        d = MessageToDict(req, preserving_proto_field_name=True)
    else:
        import json
        d = json.loads(body)
    return d.get("resource_metrics", d.get("resourceMetrics", []))


def decode_logs(body: bytes, content_type: str) -> list[dict]:
    if content_type == PROTO_CT:
        req = ExportLogsServiceRequest()
        req.ParseFromString(body)
        d = MessageToDict(req, preserving_proto_field_name=True)
    else:
        import json
        d = json.loads(body)
    return d.get("resource_logs", d.get("resourceLogs", []))


def encode_trace_response(content_type: str) -> bytes:
    if content_type == PROTO_CT:
        return ExportTraceServiceResponse().SerializeToString()
    return b'{"partialSuccess":{}}'


def encode_metrics_response(content_type: str) -> bytes:
    if content_type == PROTO_CT:
        return ExportMetricsServiceResponse().SerializeToString()
    return b'{"partialSuccess":{}}'


def encode_logs_response(content_type: str) -> bytes:
    if content_type == PROTO_CT:
        return ExportLogsServiceResponse().SerializeToString()
    return b'{"partialSuccess":{}}'
