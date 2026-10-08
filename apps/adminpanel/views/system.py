import os
import platform
import shutil
import time
from collections import deque
from pathlib import Path

import django
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomUser, UserDevice
from apps.education.models import (
    Category, DataCard, DataCardLog, DataCardMedia, Module, ModuleComment,
    ModuleFeedback, ModuleLog, ModuleQuestion, Score, Test, TestAnswer,
)
from apps.news.models import Feedback, News, NewsLog, Question
from apps.notifications.models import EmergencyNotification, Notification
from apps.society.models import Choice, ChoiceMember
from apps.wallet.models import CoinTransaction
from .. import metrics
from ..mixins import AdminAPIMixin

LOG_FILES = {"errors": "errors.log", "django": "django.log"}
MEDIA_SIZE_CACHE_KEY = "adminpanel:media_usage"

TABLES = (
    ("Foydalanuvchilar", CustomUser), ("Qurilmalar", UserDevice),
    ("Kategoriyalar", Category), ("Modullar", Module), ("DataCardlar", DataCard),
    ("DataCard media", DataCardMedia), ("Testlar", Test), ("Test javoblari", TestAnswer),
    ("Modul loglari", ModuleLog), ("DataCard loglari", DataCardLog), ("Ballar", Score),
    ("Modul savollari", ModuleQuestion), ("Modul izohlari", ModuleComment),
    ("Modul reaksiyalari", ModuleFeedback), ("Yangiliklar", News), ("Yangilik o'qishlari", NewsLog),
    ("Murojaatlar", Feedback), ("FAQ", Question), ("Tanlovlar", Choice),
    ("Tanlov a'zolari", ChoiceMember), ("Coin tranzaksiyalari", CoinTransaction),
    ("Bildirishnomalar", Notification), ("Favqulodda xabarlar", EmergencyNotification),
)


def _timed(fn):
    started = time.monotonic()
    try:
        detail = fn()
        return {"ok": True, "latency_ms": round((time.monotonic() - started) * 1000, 1), **(detail or {})}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def _check_database():
    info = {"vendor": connection.vendor}
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        if connection.vendor == "postgresql":
            cursor.execute("SELECT current_setting('server_version'), pg_database_size(current_database())")
            version, size = cursor.fetchone()
            info.update({"version": version, "size_bytes": size})
    return info


def _check_cache():
    key = "adminpanel:health"
    cache.set(key, "1", 10)
    if cache.get(key) != "1":
        raise RuntimeError("Cache qiymatni qaytarmadi")


def _check_celery():
    from config.celery import app
    replies = app.control.ping(timeout=1.0) or []
    workers = [name for reply in replies for name in reply]
    if not workers:
        raise RuntimeError("Celery worker javob bermadi")
    return {"workers": workers}


def _git_commit():
    try:
        git_dir = Path(settings.BASE_DIR) / ".git"
        head = (git_dir / "HEAD").read_text().strip()
        if head.startswith("ref:"):
            ref = head.split(" ", 1)[1]
            return {"branch": ref.rsplit("/", 1)[-1], "commit": (git_dir / ref).read_text().strip()[:10]}
        return {"branch": None, "commit": head[:10]}
    except Exception:
        return None


def _media_usage():
    cached = cache.get(MEDIA_SIZE_CACHE_KEY)
    if cached:
        return cached
    folders, total = [], 0
    root = Path(settings.MEDIA_ROOT)
    if root.exists():
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            size = files = 0
            for dirpath, _, filenames in os.walk(entry):
                for name in filenames:
                    try:
                        size += os.path.getsize(os.path.join(dirpath, name))
                        files += 1
                    except OSError:
                        pass
            folders.append({"name": entry.name, "size_bytes": size, "files": files})
            total += size
    usage = {"total_bytes": total, "folders": folders}
    cache.set(MEDIA_SIZE_CACHE_KEY, usage, 300)
    return usage


def _host():
    info = {"cpu_count": os.cpu_count()}
    try:
        info["load_avg"] = [round(x, 2) for x in os.getloadavg()]
    except (OSError, AttributeError):
        pass
    try:
        disk = shutil.disk_usage(settings.BASE_DIR)
        info["disk"] = {"total_bytes": disk.total, "used_bytes": disk.used, "free_bytes": disk.free}
    except OSError:
        pass
    try:
        mem = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                key, value = line.split(":", 1)
                if key in ("MemTotal", "MemAvailable"):
                    mem[key] = int(value.strip().split()[0]) * 1024
        if mem:
            info["memory"] = {"total_bytes": mem.get("MemTotal"), "available_bytes": mem.get("MemAvailable")}
    except OSError:
        pass
    return info


class SystemView(AdminAPIMixin, APIView):
    def get(self, request):
        safe_cache = _timed(_check_cache)
        try:
            media = _media_usage()
        except Exception:
            media = None
        return Response({
            "server_time": timezone.now(),
            "services": {
                "database": _timed(_check_database),
                "cache": safe_cache,
                "celery": _timed(_check_celery),
            },
            "app": {
                "debug": settings.DEBUG,
                "django": django.get_version(),
                "python": platform.python_version(),
                "time_zone": settings.TIME_ZONE,
                "git": _git_commit(),
            },
            "host": _host(),
            "media": media,
            "tables": [{"name": name, "rows": model.objects.count()} for name, model in TABLES],
            "requests": metrics.read(24),
        })


class SystemLogsView(AdminAPIMixin, APIView):
    def get(self, request):
        name = request.query_params.get("file", "errors")
        if name not in LOG_FILES:
            return Response({"detail": "Noma'lum log fayli."}, status=400)
        try:
            lines = max(10, min(int(request.query_params.get("lines", 200)), 1000))
        except ValueError:
            lines = 200

        path = Path(settings.LOG_DIR) / LOG_FILES[name]
        if not path.exists():
            return Response({"file": name, "available": False, "lines": []})
        try:
            with open(path, "r", errors="replace") as fh:
                tail = list(deque(fh, maxlen=lines))
            stat = path.stat()
        except OSError as exc:
            return Response({"file": name, "available": False, "error": str(exc), "lines": []})
        return Response({
            "file": name,
            "available": True,
            "size_bytes": stat.st_size,
            "modified_at": timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
            "lines": [line.rstrip("\n") for line in tail],
        })
