"""Middleware components for the SODAV Monitor system.

This module contains FastAPI middlewares for request processing and metrics collection,
including Prometheus metrics and system resource monitoring.
"""

import asyncio
import time

import psutil
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .metrics import HTTP_REQUEST_COUNT, HTTP_REQUEST_LATENCY, update_system_metrics


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting Prometheus metrics on HTTP requests.

    This middleware tracks request counts and latencies for each endpoint,
    excluding specified paths like health checks and metrics endpoints.
    """

    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        """Initialize the Prometheus middleware.

        Args:
            app: The ASGI application to wrap
            exclude_paths: List of URL paths to exclude from metrics collection
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/favicon.ico"]

    async def dispatch(self, request: Request, call_next):
        """Process an HTTP request and collect metrics.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler in the chain

        Returns:
            Response: The HTTP response from the application

        Raises:
            Exception: Any exception from the application is re-raised after metrics collection
        """
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            status_code = "500"
            raise e
        finally:
            duration = time.time() - start_time
            HTTP_REQUEST_COUNT.labels(
                method=request.method, endpoint=request.url.path, status=status_code
            ).inc()
            HTTP_REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(
                duration
            )

        return response


class SystemMetricsCollector:
    """Background service for collecting system metrics.

    This class runs a background task that periodically collects system metrics
    like CPU usage and memory consumption, updating Prometheus metrics accordingly.
    """

    def __init__(self, interval: int = 15):
        """Initialize the system metrics collector.

        Args:
            interval: Collection interval in seconds (default: 15)
        """
        self.interval = interval
        self.is_running = False
        self.task = None

    async def collect_metrics(self):
        """Periodically collect and update system metrics.

        This method runs in a loop until stopped, collecting CPU and memory metrics
        at the specified interval and updating the corresponding Prometheus metrics.
        """
        while self.is_running:
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            update_system_metrics(memory_bytes=memory_info.used, cpu_percent=cpu_percent)

            await asyncio.sleep(self.interval)

    def start(self):
        """Start the background metrics collection task."""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.collect_metrics())

    def stop(self):
        """Stop the background metrics collection task."""
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
