"""In-memory telemetry store with bounded size."""

import threading
from collections import deque
from datetime import datetime, timezone


class TelemetryStore:
    def __init__(self, max_items: int = 500):
        self._lock = threading.Lock()
        self._traces = deque(maxlen=max_items)
        self._metrics = deque(maxlen=max_items)
        self._logs = deque(maxlen=max_items)
        self._counts = {"traces": 0, "metrics": 0, "logs": 0}

    def add_traces(self, resource_spans: list[dict]):
        with self._lock:
            for rs in resource_spans:
                self._traces.append({
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "data": rs,
                })
                self._counts["traces"] += 1

    def add_metrics(self, resource_metrics: list[dict]):
        with self._lock:
            for rm in resource_metrics:
                self._metrics.append({
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "data": rm,
                })
                self._counts["metrics"] += 1

    def add_logs(self, resource_logs: list[dict]):
        with self._lock:
            for rl in resource_logs:
                self._logs.append({
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "data": rl,
                })
                self._counts["logs"] += 1

    def get_traces(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._traces)[-limit:]

    def get_metrics(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._metrics)[-limit:]

    def get_logs(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._logs)[-limit:]

    def get_counts(self) -> dict:
        with self._lock:
            return dict(self._counts)

    def clear(self):
        with self._lock:
            self._traces.clear()
            self._metrics.clear()
            self._logs.clear()
            self._counts = {"traces": 0, "metrics": 0, "logs": 0}


store = TelemetryStore()
