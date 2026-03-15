"""Observability auto-setup for flask-apcore.

Reads ApcoreSettings and creates tracing, metrics, and logging middleware
instances. Called during Apcore.init_app() to populate the ext_data dict
with observability middleware that will be injected into the Executor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.config import ApcoreSettings

logger = logging.getLogger("flask_apcore")


def setup_observability(settings: ApcoreSettings, ext_data: dict[str, Any]) -> None:
    """Configure observability middleware from settings.

    Inspects ``settings.tracing_enabled``, ``settings.metrics_enabled``,
    and ``settings.logging_enabled`` to create the appropriate apcore
    middleware instances.

    Results are stored in *ext_data*:
    - ``ext_data["observability_middlewares"]``: list of middleware instances
    - ``ext_data["metrics_collector"]``: MetricsCollector instance (or None)

    Args:
        settings: Validated ApcoreSettings from load_settings().
        ext_data: Mutable dict that will be stored in app.extensions["apcore"].
    """
    middlewares: list[Any] = []
    metrics_collector = None

    # --- Tracing ---
    if settings.tracing_enabled:
        from apcore.observability.tracing import (
            InMemoryExporter,
            OTLPExporter,
            StdoutExporter,
            TracingMiddleware,
        )

        if settings.tracing_exporter == "memory":
            exporter = InMemoryExporter()
        elif settings.tracing_exporter == "otlp":
            kwargs: dict[str, Any] = {}
            if settings.tracing_otlp_endpoint is not None:
                kwargs["endpoint"] = settings.tracing_otlp_endpoint
            if settings.tracing_service_name:
                kwargs["service_name"] = settings.tracing_service_name
            exporter = OTLPExporter(**kwargs)
        else:
            # Default: stdout
            exporter = StdoutExporter()

        tracing_mw = TracingMiddleware(exporter=exporter)
        middlewares.append(tracing_mw)
        logger.debug(
            "Observability: tracing enabled (exporter=%s)",
            settings.tracing_exporter,
        )

    # --- Metrics ---
    if settings.metrics_enabled:
        from apcore.observability.metrics import MetricsCollector, MetricsMiddleware

        if settings.metrics_buckets is not None:
            metrics_collector = MetricsCollector(buckets=settings.metrics_buckets)
        else:
            metrics_collector = MetricsCollector()

        metrics_mw = MetricsMiddleware(collector=metrics_collector)
        middlewares.append(metrics_mw)
        logger.debug("Observability: metrics enabled")

    # --- Logging ---
    if settings.logging_enabled:
        from apcore.observability.context_logger import (
            ContextLogger,
            ObsLoggingMiddleware,
        )

        obs_logger = ContextLogger(
            name="apcore.obs_logging",
            output_format=settings.logging_format,
            level=settings.logging_level.lower(),
        )
        logging_mw = ObsLoggingMiddleware(logger=obs_logger)
        middlewares.append(logging_mw)
        logger.debug(
            "Observability: logging enabled (format=%s, level=%s)",
            settings.logging_format,
            settings.logging_level,
        )

    # --- Error History ---
    if settings.tracing_enabled or settings.metrics_enabled or settings.logging_enabled:
        from apcore.observability import ErrorHistory
        from apcore.middleware import ErrorHistoryMiddleware

        error_history = ErrorHistory()
        error_history_mw = ErrorHistoryMiddleware(error_history=error_history)
        middlewares.append(error_history_mw)
        ext_data["error_history"] = error_history
        logger.debug("Observability: error history enabled")

    # --- Usage Tracking ---
    if settings.metrics_enabled:
        from apcore.observability import UsageCollector, UsageMiddleware

        usage_collector = UsageCollector()
        usage_mw = UsageMiddleware(collector=usage_collector)
        middlewares.append(usage_mw)
        ext_data["usage_collector"] = usage_collector
        logger.debug("Observability: usage tracking enabled")

    # --- Platform Notify ---
    if settings.sys_modules_events_enabled and metrics_collector is not None:
        from apcore import EventEmitter
        from apcore.middleware import PlatformNotifyMiddleware

        event_emitter = EventEmitter()
        platform_mw = PlatformNotifyMiddleware(
            event_emitter=event_emitter,
            metrics_collector=metrics_collector,
        )
        middlewares.append(platform_mw)
        ext_data["event_emitter"] = event_emitter
        logger.debug("Observability: platform notify enabled")

    ext_data["observability_middlewares"] = middlewares
    ext_data["metrics_collector"] = metrics_collector
