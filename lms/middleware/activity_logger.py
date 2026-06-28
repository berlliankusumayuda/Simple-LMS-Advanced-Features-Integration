"""
Activity Logger Middleware
Mencatat aktivitas user ke MongoDB secara asynchronous via Celery.
"""
import logging

logger = logging.getLogger(__name__)

LOGGED_PATHS = ['/api/']


class ActivityLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if (request.user.is_authenticated and
                    any(request.path.startswith(p) for p in LOGGED_PATHS) and
                    response.status_code < 500):
                self._async_log(request, response)
        except Exception as e:
            logger.error(f"ActivityLogger error: {e}")
        return response

    def _async_log(self, request, response):
        try:
            from lms.tasks.analytics_tasks import log_user_activity
            action = self._determine_action(request)
            if action:
                log_user_activity.delay(
                    user_id=request.user.id,
                    username=request.user.username,
                    action=action,
                    path=request.path,
                    method=request.method,
                    ip_address=self._get_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    status_code=response.status_code,
                )
        except Exception as e:
            logger.error(f"Async log error: {e}")

    def _determine_action(self, request):
        path = request.path
        method = request.method
        if '/enrollments/' in path and method == 'POST':
            return 'course_enroll'
        elif '/courses/' in path and method == 'GET':
            return 'course_view'
        elif '/lessons/' in path and method == 'GET':
            return 'lesson_start'
        elif '/progress/' in path and method in ['POST', 'PUT']:
            return 'lesson_complete'
        elif '/reports/' in path:
            return 'report_export'
        return None

    def _get_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
