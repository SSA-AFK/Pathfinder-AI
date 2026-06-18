"""语义缓存：基于输入 MD5 的内存缓存，降低重复查询成本。"""

import hashlib
import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class CacheManager:
    """内存缓存管理器，线程安全。

    用法:
        cache = CacheManager()
        cache.set("product|persona", {"stages": [...], ...})
        hit, data = cache.get("product|persona")
    """

    def __init__(self, ttl: int = 0, max_entries: int = 1000):
        self._store: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl  # 秒，0 = 永不过期
        self._max_entries = max_entries

    @staticmethod
    def make_key(product: str, persona: str) -> str:
        """归一化输入并计算 MD5 作为缓存 key。"""
        normalised = f"{product.strip().lower()}|{persona.strip().lower()}"
        return hashlib.md5(normalised.encode("utf-8")).hexdigest()

    def get(self, product: str, persona: str) -> tuple[bool, dict | None]:
        """查询缓存，返回 (命中?, 数据 dict 或 None)。"""
        key = self.make_key(product, persona)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False, None
            ts, data = entry
            if self._ttl > 0 and time.monotonic() - ts > self._ttl:
                del self._store[key]
                return False, None
            return True, data

    def set(self, product: str, persona: str, data: dict) -> None:
        """写入缓存。"""
        key = self.make_key(product, persona)
        with self._lock:
            # 清理过期条目
            if len(self._store) >= self._max_entries:
                cutoff = time.monotonic() - (self._ttl or 3600)
                expired = [k for k, v in self._store.items() if v[0] < cutoff]
                for k in expired:
                    del self._store[k]
                # 如果仍满，淘汰最旧条目
                if len(self._store) >= self._max_entries:
                    oldest = min(self._store.items(), key=lambda x: x[1][0])
                    del self._store[oldest[0]]
                    logger.info("缓存淘汰: %s", oldest[0][:8])
            self._store[key] = (time.monotonic(), data)
            logger.info("缓存写入: %s (%d 条目)", key[:8], len(self._store))

    def stats(self) -> dict[str, Any]:
        """返回缓存统计信息。"""
        with self._lock:
            return {
                "entries": len(self._store),
                "ttl_seconds": self._ttl,
                "max_entries": self._max_entries,
            }


# 全局实例，由 main.py 初始化
_cache: CacheManager | None = None


def get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        ttl = int(os.getenv("CACHE_TTL", "0"))
        max_entries = int(os.getenv("CACHE_MAX_ENTRIES", "1000"))
        _cache = CacheManager(ttl=ttl, max_entries=max_entries)
        logger.info("缓存初始化: TTL=%ss, max=%d 条目", ttl, max_entries)
    return _cache


def cost_saved() -> float:
    """估算单次调用节省的成本（美元）。"""
    # deepseek-chat ≈ $0.07/10K tokens（约一次简单调用的典型成本）
    return float(os.getenv("CACHE_COST_PER_CALL", "0.07"))
