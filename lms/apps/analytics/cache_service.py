"""
Redis Caching Service
Implementasi caching patterns untuk LMS
"""
import json
import logging
from functools import wraps
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service layer untuk Redis caching operations.
    Implementasi caching patterns: Cache-aside, Write-through, TTL management.
    """

    # ============================================================
    # COURSE LIST CACHING
    # ============================================================
    @staticmethod
    def get_course_list_key(page=1, page_size=10, search='', category='', status='published'):
        """Generate cache key untuk course list dengan filter parameters."""
        return f"courses:list:p{page}:ps{page_size}:s{search}:c{category}:st{status}"

    @staticmethod
    def get_cached_course_list(page=1, page_size=10, search='', category='', status='published'):
        """
        Ambil course list dari cache.
        Returns: cached data atau None jika tidak ada.
        """
        key = CacheService.get_course_list_key(page, page_size, search, category, status)
        cached = cache.get(key)
        if cached:
            logger.debug(f"Cache HIT: {key}")
            return cached
        logger.debug(f"Cache MISS: {key}")
        return None

    @staticmethod
    def set_cached_course_list(data, page=1, page_size=10, search='', category='', status='published'):
        """
        Simpan course list ke cache.
        TTL: 5 menit (300 detik)
        """
        key = CacheService.get_course_list_key(page, page_size, search, category, status)
        timeout = settings.CACHE_TIMEOUTS.get('course_list', 300)
        cache.set(key, data, timeout=timeout)
        logger.debug(f"Cache SET: {key} (TTL: {timeout}s)")

    # ============================================================
    # COURSE DETAIL CACHING
    # ============================================================
    @staticmethod
    def get_course_detail_key(course_id):
        """Generate cache key untuk course detail."""
        return f"courses:detail:{course_id}"

    @staticmethod
    def get_cached_course_detail(course_id):
        """Ambil course detail dari cache."""
        key = CacheService.get_course_detail_key(course_id)
        cached = cache.get(key)
        if cached:
            logger.debug(f"Cache HIT: {key}")
            return cached
        logger.debug(f"Cache MISS: {key}")
        return None

    @staticmethod
    def set_cached_course_detail(course_id, data):
        """
        Simpan course detail ke cache.
        TTL: 10 menit (600 detik)
        """
        key = CacheService.get_course_detail_key(course_id)
        timeout = settings.CACHE_TIMEOUTS.get('course_detail', 600)
        cache.set(key, data, timeout=timeout)
        logger.debug(f"Cache SET: {key} (TTL: {timeout}s)")

    # ============================================================
    # CACHE INVALIDATION STRATEGY
    # ============================================================
    @staticmethod
    def invalidate_course_cache(course_id):
        """
        Invalidate semua cache yang berkaitan dengan course tertentu.
        Dipanggil saat course diupdate, enrollment terjadi, dll.

        Strategy: Targeted invalidation - hanya hapus cache yang relevan.
        """
        # 1. Hapus course detail cache
        detail_key = CacheService.get_course_detail_key(course_id)
        cache.delete(detail_key)
        logger.info(f"Cache INVALIDATED: {detail_key}")

        # 2. Hapus course statistics cache
        stats_key = f"courses:stats:{course_id}"
        cache.delete(stats_key)
        logger.info(f"Cache INVALIDATED: {stats_key}")

        # 3. Hapus semua course list cache (karena list bisa berubah)
        # Menggunakan pattern deletion dengan prefix
        CacheService.invalidate_course_list_cache()

    @staticmethod
    def invalidate_course_list_cache():
        """
        Invalidate semua course list cache.
        Dipanggil saat ada perubahan yang mempengaruhi list (add/update/delete course).

        Menggunakan django-redis delete_pattern untuk bulk deletion.
        """
        try:
            from django_redis import get_redis_connection
            redis_client = get_redis_connection('default')
            # Hapus semua key dengan prefix courses:list:*
            pattern = "lms:1:courses:list:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Cache INVALIDATED: {len(keys)} course list keys")
        except Exception as e:
            logger.error(f"Error invalidating course list cache: {e}")

    @staticmethod
    def invalidate_all_course_caches():
        """
        Invalidate SEMUA course-related cache.
        Digunakan dengan hati-hati - hanya untuk maintenance/emergency.
        """
        try:
            from django_redis import get_redis_connection
            redis_client = get_redis_connection('default')
            pattern = "lms:1:courses:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                logger.warning(f"FULL CACHE CLEAR: {len(keys)} course keys deleted")
        except Exception as e:
            logger.error(f"Error clearing all course caches: {e}")

    # ============================================================
    # COURSE STATISTICS CACHING
    # ============================================================
    @staticmethod
    def get_cached_course_statistics(course_id):
        """Ambil course statistics dari cache."""
        key = f"courses:stats:{course_id}"
        return cache.get(key)

    @staticmethod
    def set_cached_course_statistics(course_id, data):
        """Simpan course statistics ke cache. TTL: 30 menit."""
        key = f"courses:stats:{course_id}"
        timeout = settings.CACHE_TIMEOUTS.get('course_statistics', 1800)
        cache.set(key, data, timeout=timeout)


def cache_course_detail(timeout=600):
    """
    Decorator untuk caching course detail views.

    Usage:
        @cache_course_detail(timeout=600)
        def get_course(self, request, pk):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract course_id dari kwargs
            course_id = kwargs.get('pk') or kwargs.get('course_id')
            if not course_id:
                return func(*args, **kwargs)

            # Cek cache
            cached = CacheService.get_cached_course_detail(course_id)
            if cached is not None:
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Simpan ke cache
            CacheService.set_cached_course_detail(course_id, result)
            return result
        return wrapper
    return decorator


class RedisCacheMonitor:
    """
    Utility untuk monitoring Redis cache performance.
    """

    @staticmethod
    def get_cache_stats():
        """
        Ambil statistik cache dari Redis.
        Returns dict dengan info: hits, misses, memory usage, dll.
        """
        try:
            from django_redis import get_redis_connection
            redis_client = get_redis_connection('default')
            info = redis_client.info()

            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': _calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                ),
                'total_keys': _count_lms_keys(redis_client),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    @staticmethod
    def get_key_ttl(key):
        """Cek TTL dari specific cache key."""
        try:
            from django_redis import get_redis_connection
            redis_client = get_redis_connection('default')
            return redis_client.ttl(f"lms:1:{key}")
        except Exception:
            return -1


def _calculate_hit_rate(hits, misses):
    """Hitung cache hit rate percentage."""
    total = hits + misses
    if total == 0:
        return 0.0
    return round((hits / total) * 100, 2)


def _count_lms_keys(redis_client):
    """Hitung jumlah LMS cache keys."""
    try:
        keys = redis_client.keys("lms:1:*")
        return len(keys)
    except Exception:
        return 0
