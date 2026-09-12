"""Structured request logging and lightweight process metrics."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Request

REQUESTS: Counter[str] = Counter()
STARTED_AT = time.monotonic()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(
        level=logging.getLevelName(__import__("os").getenv("LOG_LEVEL", "INFO").upper()),
        handlers=[handler],
        force=True,
    )


def install_observability(app: FastAPI) -> None:
    logger = logging.getLogger("aether.backend.request")

    @app.middleware("http")
    async def request_observer(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            REQUESTS["errors"] += 1
            logger.exception(
                "request failed",
                extra={"request_id": request_id, "method": request.method, "path": request.url.path},
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        REQUESTS["total"] += 1
        REQUESTS[f"status_{response.status_code}"] += 1
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


def metrics_snapshot() -> Dict[str, Any]:
    return {"uptime_seconds": round(time.monotonic() - STARTED_AT), "requests": dict(REQUESTS)}
