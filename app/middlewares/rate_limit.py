import time
from collections import deque
from typing import Deque, Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory per-IP rate limiter:
    - 10 requests per 60 seconds
    - 100 requests per 3600 seconds
    Fixed-window-ish using timestamp deques (sliding window).
    """

    def __init__(self, app, per_minute: int = 10, per_hour: int = 100):
        super().__init__(app)
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.window_min = 60
        self.window_hour = 3600

        # ip -> (deque_minute, deque_hour)
        self.store: Dict[str, Tuple[Deque[float], Deque[float]]] = {}

    def _get_ip(self, request: Request) -> str:
        # 生产环境通常从 X-Forwarded-For 取，这里先兼容本地
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # 取第一个 IP
            return xff.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _prune(self, dq: Deque[float], now: float, window: int) -> None:
        while dq and dq[0] <= now - window:
            dq.popleft()

    async def dispatch(self, request: Request, call_next) -> Response:
        # 只限流你的 public search（可按题目要求扩大范围）
        if request.url.path != "/api/stores/search":
            return await call_next(request)

        ip = self._get_ip(request)
        now = time.time()

        if ip not in self.store:
            self.store[ip] = (deque(), deque())

        dq_min, dq_hour = self.store[ip]

        # sliding window prune
        self._prune(dq_min, now, self.window_min)
        self._prune(dq_hour, now, self.window_hour)

        # check limits
        if len(dq_min) >= self.per_minute:
            retry_after = int(dq_min[0] + self.window_min - now) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded: 10 requests per minute"},
                headers={
                    "Retry-After": str(max(retry_after, 1)),
                    "X-RateLimit-Limit-Minute": str(self.per_minute),
                    "X-RateLimit-Remaining-Minute": "0",
                },
            )

        if len(dq_hour) >= self.per_hour:
            retry_after = int(dq_hour[0] + self.window_hour - now) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded: 100 requests per hour"},
                headers={
                    "Retry-After": str(max(retry_after, 1)),
                    "X-RateLimit-Limit-Hour": str(self.per_hour),
                    "X-RateLimit-Remaining-Hour": "0",
                },
            )

        # record this request
        dq_min.append(now)
        dq_hour.append(now)

        # proceed
        resp = await call_next(request)

        # (可选) 返回剩余额度（不是必须，但加分）
        self._prune(dq_min, time.time(), self.window_min)
        self._prune(dq_hour, time.time(), self.window_hour)
        resp.headers["X-RateLimit-Limit-Minute"] = str(self.per_minute)
        resp.headers["X-RateLimit-Remaining-Minute"] = str(max(self.per_minute - len(dq_min), 0))
        resp.headers["X-RateLimit-Limit-Hour"] = str(self.per_hour)
        resp.headers["X-RateLimit-Remaining-Hour"] = str(max(self.per_hour - len(dq_hour), 0))
        return resp
