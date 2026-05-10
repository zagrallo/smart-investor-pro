import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    latency_ms: float = 0.0
    total_calls: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return round(self.hits / self.total_calls, 3)

    def record(self, hit: bool, latency: float):
        self.total_calls += 1
        if hit:
            self.hits += 1
        else:
            self.misses += 1
        self.latency_ms = round(
            (self.latency_ms * (self.total_calls - 1) + latency) / self.total_calls, 2
        )


class SmartCache:
    def __init__(self):
        self._memory: dict[str, tuple[float, Any]] = {}
        self._redis = None
        self._redis_ok = False
        self.stats = CacheStats()
        self._init_redis()

    def _init_redis(self):
        url = settings.REDIS_URL
        if not url or not url.startswith("redis://"):
            return
        try:
            import redis.asyncio as aredis

            self._redis = aredis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
            logger.info("Redis configured, will verify on first use: %s", url)
        except Exception as e:
            logger.warning("Redis init failed: %s", e)

    async def _ensure_redis(self) -> bool:
        if self._redis_ok:
            return True
        if self._redis is None:
            return False
        try:
            await self._redis.ping()
            self._redis_ok = True
            logger.info("Redis connected")
            return True
        except Exception as e:
            logger.debug("Redis ping failed: %s", e)
            self._redis_ok = False
            return False

    async def get(self, key: str) -> Any | None:
        t0 = time.perf_counter()
        try:
            if await self._ensure_redis():
                val = await self._redis.get(key)
                if val is not None:
                    self.stats.record(True, (time.perf_counter() - t0) * 1000)
                    return json.loads(val)
            entry = self._memory.get(key)
            if entry is not None:
                expires, val = entry
                if expires > time.time():
                    self.stats.record(True, (time.perf_counter() - t0) * 1000)
                    return val
                else:
                    del self._memory[key]
        except Exception as e:
            logger.debug("Cache get error: %s", e)
        self.stats.record(False, (time.perf_counter() - t0) * 1000)
        return None

    async def set(self, key: str, value: Any, ttl: int):
        try:
            if await self._ensure_redis():
                await self._redis.setex(key, ttl, json.dumps(value, default=str))
            self._memory[key] = (time.time() + ttl, value)
        except Exception as e:
            logger.debug("Cache set error: %s", e)

    async def clear(self, pattern: str = ""):
        try:
            if await self._ensure_redis():
                if pattern:
                    cursor = 0
                    while True:
                        cursor, keys = await self._redis.scan(cursor, match=pattern)
                        if keys:
                            await self._redis.delete(*keys)
                        if cursor == 0:
                            break
                else:
                    await self._redis.flushdb()
        except Exception:
            pass
        if pattern:
            self._memory = {k: v for k, v in self._memory.items() if pattern not in k}
        else:
            self._memory.clear()
        logger.info("Cache cleared (pattern=%s)", pattern or "*")

    async def close(self):
        try:
            if self._redis:
                await self._redis.aclose()
        except Exception:
            pass
        self._redis_ok = False
        self._redis = None

    def summary(self) -> dict:
        return {
            "mode": "redis" if self._redis_ok else ("memory" if not settings.REDIS_URL else "redis_unavailable"),
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "total_calls": self.stats.total_calls,
            "hit_rate": self.stats.hit_rate,
            "avg_latency_ms": self.stats.latency_ms,
        }


def hash_key(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


_cache: SmartCache | None = None


def get_cache() -> SmartCache:
    global _cache
    if _cache is None:
        _cache = SmartCache()
    return _cache


async def cached(
    key: str,
    ttl: int,
    fetcher: Callable,
    *args,
    **kwargs,
) -> tuple[Any, bool]:
    c = get_cache()
    hit = await c.get(key)
    if hit is not None:
        return hit, True
    value = await fetcher(*args, **kwargs)
    if value is not None:
        await c.set(key, value, ttl)
    return value, False
