"""
Rate Limiting Middleware
Implementasi sliding window rate limiting menggunakan Redis.
Limit: 60 requests per minute per user/IP.
"""
import time
import logging
from django.http import JsonResponse
from django.core.cache import caches
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Sliding Window Rate Limiter berbasis Redis.

    Algoritma:
    1. Setiap request, tambahkan timestamp ke Redis sorted set
    2. Hapus entries yang lebih lama dari window (1 menit)
    3. Hitung jumlah requests dalam window
    4. Jika melebihi limit, tolak request dengan 429

    Key format: ratelimit:<identifier>
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = settings.RATE_LIMIT_REQUESTS   # 60
        self.window = settings.RATE_LIMIT_WINDOW          # 60 seconds
        # Endpoints yang dikecualikan dari rate limiting
        self.exempt_paths = [
            '/admin/',
            '/health/',
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        # Skip rate limiting untuk exempt paths
        if self._is_exempt(request.path):
            return self.get_response(request)

        identifier = self._get_identifier(request)
        is_allowed, current_count, reset_time = self._check_rate_limit(identifier)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded: {identifier} - {current_count} requests in {self.window}s"
            )
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'message': f'Maksimal {self.rate_limit} request per menit. Coba lagi dalam {reset_time} detik.',
                    'retry_after': reset_time,
                },
                status=429,
                headers={
                    'X-RateLimit-Limit': str(self.rate_limit),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(reset_time),
                    'Retry-After': str(reset_time),
                }
            )

        response = self.get_response(request)

        # Tambahkan rate limit headers ke response
        remaining = max(0, self.rate_limit - current_count)
        response['X-RateLimit-Limit'] = str(self.rate_limit)
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Window'] = str(self.window)

        return response

    def _get_identifier(self, request):
        """
        Tentukan identifier untuk rate limiting.
        Prioritas: User ID (authenticated) > IP Address (anonymous)
        """
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        return f"ip:{self._get_client_ip(request)}"

    def _get_client_ip(self, request):
        """Ambil IP address client, handle proxy."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _check_rate_limit(self, identifier):
        """
        Cek apakah identifier masih dalam batas rate limit.

        Returns: (is_allowed, current_count, seconds_until_reset)
        """
        try:
            rate_cache = caches['rate_limit']
            redis_client = rate_cache.client.get_client()

            now = time.time()
            window_start = now - self.window
            key = f"ratelimit:{identifier}"

            # Sliding window menggunakan Redis sorted set
            pipe = redis_client.pipeline()
            # 1. Hapus entries di luar window
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. Tambahkan request sekarang
            pipe.zadd(key, {str(now): now})
            # 3. Hitung total requests dalam window
            pipe.zcard(key)
            # 4. Set expiry untuk auto cleanup
            pipe.expire(key, self.window * 2)
            results = pipe.execute()

            current_count = results[2]
            is_allowed = current_count <= self.rate_limit

            # Hitung waktu reset (kapan request pertama dalam window akan expire)
            if not is_allowed:
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    reset_time = int(self.window - (now - oldest_time)) + 1
                else:
                    reset_time = self.window
            else:
                reset_time = self.window

            return is_allowed, current_count, reset_time

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open - jika Redis error, izinkan request
            return True, 0, 0

    def _is_exempt(self, path):
        """Cek apakah path dikecualikan dari rate limiting."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)
