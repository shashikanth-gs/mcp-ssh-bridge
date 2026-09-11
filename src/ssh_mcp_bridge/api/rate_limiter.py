"""In-process sliding-window rate limiter for the REST compatibility API."""

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Cap requests per client identity within a rolling time window.

    FastMCP applies its own rate limiting to the Streamable HTTP endpoint at
    ``/mcp``. The REST compatibility routes under ``/api/v1`` are separate
    FastAPI routes that do not pass through FastMCP's middleware, so without
    this they would have no rate limit at all. This is a small, independent
    limiter applied to those routes with the same per-minute budget and the
    same client-identity rule (bearer token client_id, or "anonymous"). It
    tracks its own counters rather than sharing FastMCP's internal state, so
    a client's REST and MCP calls are budgeted separately, not against one
    combined total.
    """

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        """Record a request for client_id and return whether it is within budget."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client_id]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()

            if len(hits) >= self.max_requests:
                return False

            hits.append(now)
            return True
