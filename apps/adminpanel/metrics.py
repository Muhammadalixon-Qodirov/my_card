"""API so'rovlari bo'yicha yengil statistika (Redis'da, soatlik kesimda).

Har qanday xato yutib yuboriladi — statistika hech qachon so'rovni buzmasligi kerak.
"""
import re
import time
from datetime import timedelta

from django.utils import timezone

PREFIX = "adminpanel:metrics"
HOUR_TTL = 60 * 60 * 24 * 8
ERRORS_KEY = f"{PREFIX}:errors"
ERRORS_KEEP = 100
_ID_RE = re.compile(r"/\d+(?=/|$)")


def _redis():
    from django_redis import get_redis_connection
    return get_redis_connection("default")


def _hour_key(dt):
    return f"{PREFIX}:h:{dt.strftime('%Y%m%d%H')}"


def _paths_key(dt):
    return f"{PREFIX}:p:{dt.strftime('%Y%m%d')}"


def record(path, method, status, duration_ms):
    now = timezone.localtime()
    hour_key, paths_key = _hour_key(now), _paths_key(now)
    route = f"{method} {_ID_RE.sub('/:id', path)}"[:120]
    pipe = _redis().pipeline(transaction=False)
    pipe.hincrby(hour_key, "count", 1)
    pipe.hincrby(hour_key, f"s{status // 100}xx", 1)
    pipe.hincrby(hour_key, "ms", int(duration_ms))
    pipe.expire(hour_key, HOUR_TTL)
    pipe.hincrby(paths_key, route, 1)
    pipe.expire(paths_key, HOUR_TTL)
    if status >= 500:
        pipe.lpush(ERRORS_KEY, f"{now.isoformat()}|{status}|{method}|{path[:200]}")
        pipe.ltrim(ERRORS_KEY, 0, ERRORS_KEEP - 1)
    pipe.execute()


class ApiMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        try:
            path = request.path
            if path.startswith("/api/") and not path.startswith("/api/v1/admin-panel/"):
                record(path, request.method, response.status_code, (time.monotonic() - started) * 1000)
        except Exception:
            pass
        return response


def _decode(value):
    return value.decode() if isinstance(value, bytes) else value


def read(hours=24):
    """Oxirgi N soat statistikasi. Redis mavjud bo'lmasa available=False."""
    try:
        client = _redis()
        now = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        slots = [now - timedelta(hours=i) for i in range(hours - 1, -1, -1)]
        pipe = client.pipeline(transaction=False)
        for slot in slots:
            pipe.hgetall(_hour_key(slot))
        pipe.hgetall(_paths_key(now))
        pipe.lrange(ERRORS_KEY, 0, 29)
        *hour_rows, paths, errors = pipe.execute()
    except Exception:
        return {"available": False}

    series, totals = [], {"count": 0, "s2xx": 0, "s3xx": 0, "s4xx": 0, "s5xx": 0, "ms": 0}
    for slot, raw in zip(slots, hour_rows):
        row = {_decode(k): int(v) for k, v in raw.items()}
        count = row.get("count", 0)
        series.append({
            "hour": slot.isoformat(),
            "count": count,
            "errors": row.get("s5xx", 0),
            "client_errors": row.get("s4xx", 0),
            "avg_ms": round(row.get("ms", 0) / count, 1) if count else 0,
        })
        for key in totals:
            totals[key] += row.get(key, 0)

    top = sorted(((_decode(k), int(v)) for k, v in paths.items()), key=lambda x: x[1], reverse=True)[:12]
    parsed_errors = []
    for line in errors:
        parts = _decode(line).split("|", 3)
        if len(parts) == 4:
            parsed_errors.append({"at": parts[0], "status": int(parts[1]), "method": parts[2], "path": parts[3]})

    return {
        "available": True,
        "hours": hours,
        "total": totals["count"],
        "status": {k[1:]: totals[k] for k in ("s2xx", "s3xx", "s4xx", "s5xx")},
        "avg_ms": round(totals["ms"] / totals["count"], 1) if totals["count"] else 0,
        "series": series,
        "top_routes": [{"route": route, "count": count} for route, count in top],
        "recent_errors": parsed_errors,
    }
