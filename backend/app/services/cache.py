"""
Two-tier cache: Redis (persistent, survives restarts) with in-memory fallback.

Redis is used when REDIS_URL is set and reachable. If Redis is unavailable
the in-memory layer keeps things working so the app never hard-fails on cache.
"""

import pickle
import time
from functools import lru_cache
from typing import Any, Optional

# ---------------------------------------------------------------------------
# In-memory fallback (L2)
# ---------------------------------------------------------------------------

_MEM: dict[str, Any] = {}
_MEM_EXP: dict[str, float] = {}


def _mem_get(key: str) -> Any:
    if key in _MEM and time.monotonic() < _MEM_EXP[key]:
        return _MEM[key]
    _MEM.pop(key, None)
    _MEM_EXP.pop(key, None)
    return None


def _mem_set(key: str, value: Any, ttl: int) -> None:
    _MEM[key] = value
    _MEM_EXP[key] = time.monotonic() + ttl


# ---------------------------------------------------------------------------
# Redis client (L1)
# ---------------------------------------------------------------------------

@lru_cache()
def _get_redis():
    """Return a Redis client, or None if REDIS_URL is not configured."""
    try:
        import redis as redis_lib
        from app.config import get_settings
        url = get_settings().redis_url
        if not url:
            return None
        client = redis_lib.from_url(url, decode_responses=False, socket_connect_timeout=2)
        client.ping()
        return client
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cache_get(key: str) -> Optional[Any]:
    r = _get_redis()
    if r is not None:
        try:
            raw = r.get(key)
            if raw is not None:
                return pickle.loads(raw)
        except Exception:
            pass
    return _mem_get(key)


def cache_set(key: str, value: Any, ttl: int) -> None:
    _mem_set(key, value, ttl)
    r = _get_redis()
    if r is not None:
        try:
            r.set(key, pickle.dumps(value), ex=ttl)
        except Exception:
            pass
