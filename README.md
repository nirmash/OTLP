# OTLP Observability Stack on Embr

A complete observability pipeline running on [Embr](https://portal.embrdev.io): an instrumented app sends traces, logs, and metrics through OTLP to a viewer, Prometheus, and Grafana.

## Architecture

```
┌──────────────────┐     traces/logs      ┌──────────────────┐
│                  │ ──────────────────▶   │                  │
│   Notes App      │                      │   OTLP Receiver  │
│   (instrumented) │     metrics (OTLP)   │   (viewer UI)    │
│                  │ ──────┐              └──────────────────┘
└──────────────────┘       │
                           ▼
                  ┌──────────────────┐     query      ┌──────────────────┐
                  │                  │ ◀────────────── │                  │
                  │   Prometheus     │                 │   Grafana        │
                  │   (metrics DB)   │                 │   (dashboards)   │
                  └──────────────────┘                 └──────────────────┘
```

## Repositories

| Component | Repo | Purpose |
|-----------|------|---------|
| **OTLP Receiver** | [nirmash/OTLP](https://github.com/nirmash/OTLP) | Receives OTLP traces/metrics/logs, stores in SQLite, provides viewer UI |
| **Prometheus** | [nirmash/prometheus-embr](https://github.com/nirmash/prometheus-embr) | Prometheus with native OTLP receiver, wrapped in a Python reverse proxy |
| **Grafana** | [nirmash/grafana-embr](https://github.com/nirmash/grafana-embr) | Grafana OSS with auto-provisioned Prometheus datasource, wrapped in a Python reverse proxy |
| **Notes App** | [nirmash/simple-python-notes-app](https://github.com/nirmash/simple-python-notes-app) | Sample app instrumented with OpenTelemetry (traces, logs, metrics) |

## Full Stack Setup

### Prerequisites

- [Embr CLI](https://www.npmjs.com/package/@coreai-microsoft/embr-cli) installed and authenticated (`embr login`)
- GitHub repos above accessible to the Embr GitHub App

### Step 1: Deploy OTLP Receiver

```bash
embr quickstart --repo nirmash/OTLP --name OTLP
```

Note the URL (e.g. `https://production-otlp-XXXXXXXX.app.embr.azure`).

### Step 2: Deploy Prometheus

```bash
embr quickstart --repo nirmash/prometheus-embr --name prometheus-embr
```

Note the URL (e.g. `https://production-prometheus-embr-XXXXXXXX.app.embr.azure`).

Prometheus downloads its binary on first startup (~2s). The OTLP receiver is enabled via `--web.enable-otlp-receiver`. Wait ~30s after deployment for it to be ready.

### Step 3: Deploy Grafana

Before deploying, update the default Prometheus URL in `grafana-embr/application.py`:

```python
prom_url = os.environ.get("PROMETHEUS_URL", "https://production-prometheus-embr-XXXXXXXX.app.embr.azure")
```

Replace `XXXXXXXX` with your Prometheus environment's hash from Step 2, then push and deploy:

```bash
embr quickstart --repo nirmash/grafana-embr --name grafana-embr
```

Grafana downloads its binary on first startup (~3s). Anonymous access is enabled with Admin role. Wait ~60s for it to be ready.

### Step 4: Configure the Notes App

Update the OTLP endpoints in `simple-python-notes-app/backend/app.py`:

```python
_otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "https://production-otlp-XXXXXXXX.app.embr.azure"
_prom_endpoint = "https://production-prometheus-embr-XXXXXXXX.app.embr.azure/api/v1/otlp/v1/metrics"
```

Replace the URLs with your OTLP Receiver and Prometheus URLs from Steps 1-2, then push and deploy:

```bash
embr quickstart --repo nirmash/simple-python-notes-app --name simple-python-notes-app
```

### Step 5: Verify

Generate some traffic on the notes app:

```bash
NOTES_URL=https://production-simple-python-notes-app-XXXXXXXX.app.embr.azure

curl -X POST "$NOTES_URL/api/notes" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Hello"}'
```

Then check each component:

```bash
PROM_URL=https://production-prometheus-embr-XXXXXXXX.app.embr.azure

# Prometheus should show metrics after ~15s
curl "$PROM_URL/api/v1/label/__name__/values"

# Expected: notes_created_total, http_server_duration_milliseconds_*, etc.
```

Open the Grafana UI and explore the Prometheus datasource — all metrics are pre-configured.

## Current Deployment

| Component | URL |
|-----------|-----|
| OTLP Receiver | https://production-otlp-00229c32.app.embr.azure |
| Prometheus | https://production-prometheus-embr-1a780423.app.embr.azure |
| Grafana | https://production-grafana-embr-a006bc91.app.embr.azure |
| Notes App | https://production-simple-python-notes-app-55dceb21.app.embr.azure |

### Embr Project IDs

| Component | Project ID |
|-----------|-----------|
| OTLP Receiver | `prj_0251dba740ca4aa2bca2de50930f30aa` |
| Prometheus | `prj_c19c4d8ba40e4d4aac4f324d48605564` |
| Grafana | `prj_e1d0b9a851764417ab61f4074c8fba9d` |
| Notes App | `prj_cc2c98fd85d74ea988732dfeca906e43` |

---

## OTLP Receiver Details

### OTLP Endpoints

| Signal  | Endpoint           | Content-Type                                      |
|---------|--------------------|---------------------------------------------------|
| Traces  | `POST /v1/traces`  | `application/x-protobuf` or `application/json` |
| Metrics | `POST /v1/metrics` | `application/x-protobuf` or `application/json` |
| Logs    | `POST /v1/logs`    | `application/x-protobuf` or `application/json` |

### Viewer API

| Endpoint             | Description                                    |
|----------------------|------------------------------------------------|
| `GET /`              | Web UI                                         |
| `GET /api/telemetry` | Query stored telemetry (`?kind=traces&limit=50`) |
| `GET /api/stats`     | Counts of received traces, metrics, logs       |
| `POST /api/clear`    | Clear all stored telemetry                     |

### Run Locally

```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8008 --reload application:app
```

### Point Any OTLP Exporter Here

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://<otlp-receiver-url>
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

## Proxy Design Notes

Both Prometheus and Grafana run as standalone binaries that Embr can't build natively. The solution is a Python reverse proxy pattern:

1. **Startup**: The proxy starts immediately on port 8080 (Embr's expected port), returning `200 OK` for health checks
2. **Download**: A background thread downloads the binary tarball via `curl`
3. **Run**: After extraction, the binary starts on a local port (9090/3000)
4. **Proxy**: All requests are forwarded to the local binary via `ThreadingHTTPServer`

Key design decisions (learned from debugging):
- **`ThreadingHTTPServer`** — single-threaded `HTTPServer` causes concurrent browser requests to queue and timeout
- **`curl` for downloads** — Python's `urllib` can't reliably handle GitHub's 302 redirects + large files within socket timeouts
- **Health check interception** — `/health` must always return 200, even after the backend is ready (Grafana uses `/api/health`, not `/health`)
- **`Cache-Control: no-store`** — prevents Azure Front Door from caching startup or API responses
- **`Content-Encoding: identity`** — prevents CDN from serving gzip-compressed responses without the proper header
- **Don't forward `Accept-Encoding`** — prevents compressed responses that the proxy can't properly re-encode
