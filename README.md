# OTLP HTTP Receiver

An OpenTelemetry Protocol (OTLP) HTTP endpoint that receives traces, metrics, and logs — with a live viewer UI. Ready to deploy on [Embr](https://portal.embrdev.io).

## Deploy to Embr

This repo includes a [`build.yaml`](build.yaml) that tells Embr how to build and run the app:

```yaml
version: 1
platform: python
platformVersion: "3.14"
run:
  port: 8080
```

Connect this repo in the [Embr Portal](https://portal.embrdev.io), and Embr will install dependencies from `requirements.txt`, then start the server automatically.

## Run Locally

```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8008 --reload application:app
```

Open http://localhost:8008

## OTLP Endpoints

| Signal  | Endpoint       | Content-Type                              |
|---------|----------------|-------------------------------------------|
| Traces  | `POST /v1/traces`  | `application/x-protobuf` or `application/json` |
| Metrics | `POST /v1/metrics` | `application/x-protobuf` or `application/json` |
| Logs    | `POST /v1/logs`    | `application/x-protobuf` or `application/json` |

### Test with curl

```bash
curl -X POST http://localhost:8008/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"my-service"}}]},"scopeSpans":[{"spans":[{"traceId":"01020304050607080102030405060708","spanId":"0102030405060708","name":"test-span","kind":1,"startTimeUnixNano":"1700000000000000000","endTimeUnixNano":"1700000001000000000"}]}]}]}'
```

## Viewer API

| Endpoint             | Description                                |
|----------------------|--------------------------------------------|
| `GET /`              | Web UI                                     |
| `GET /api/telemetry` | Query stored telemetry (`?kind=traces&limit=50`) |
| `GET /api/stats`     | Counts of received traces, metrics, logs   |
| `POST /api/clear`    | Clear all stored telemetry                 |

## Point an OTLP Exporter Here

Set the exporter endpoint to this service's URL:

```
OTEL_EXPORTER_OTLP_ENDPOINT=https://<your-embr-url>
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```
