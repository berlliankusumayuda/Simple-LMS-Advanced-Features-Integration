"""
Celery Tasks - Analytics & Logging
"""
import logging
from celery import shared_task
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task(
    name='lms.tasks.analytics_tasks.log_user_activity',
    ignore_result=True,
    queue='low_priority',
)
def log_user_activity(user_id, username, action, path='', method='',
                      ip_address='', user_agent='', status_code=200,
                      resource_type=None, resource_id=None, metadata=None):
    """
    Log aktivitas user ke MongoDB ActivityLog collection.
    Fire-and-forget task - tidak perlu return value.
    """
    try:
        from lms.apps.analytics.documents import ActivityLog
        import mongoengine

        log = ActivityLog(
            user_id=user_id,
            username=username,
            action=action,
            path=path,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {'status_code': status_code},
        )
        log.save()
        logger.debug(f"Activity logged: {username} - {action}")

    except Exception as e:
        logger.error(f"Error logging activity to MongoDB: {e}")


@shared_task(
    name='lms.tasks.analytics_tasks.generate_analytics_report',
    bind=True,
)
def generate_analytics_report(self, course_id=None, date_from=None, date_to=None):
    """
    Generate aggregated analytics report dari MongoDB.
    Bisa untuk satu course atau semua courses.
    """
    try:
        from lms.apps.analytics.documents import ActivityLog, LearningSession, CourseAnalytics

        pipeline_filter = {}
        if course_id:
            pipeline_filter['resource_id'] = course_id

        # Aggregation query: activity count per action type
        pipeline = [
            {'$match': pipeline_filter},
            {'$group': {
                '_id': '$action',
                'count': {'$sum': 1},
                'unique_users': {'$addToSet': '$user_id'},
            }},
            {'$project': {
                'action': '$_id',
                'count': 1,
                'unique_user_count': {'$size': '$unique_users'},
            }},
            {'$sort': {'count': -1}},
        ]

        results = list(ActivityLog.objects.aggregate(*pipeline))

        report_data = {
            'generated_at': datetime.now().isoformat(),
            'course_id': course_id,
            'activity_summary': results,
        }

        logger.info(f"Analytics report generated: course_id={course_id}")
        return report_data

    except Exception as exc:
        logger.error(f"Error generating analytics report: {exc}")
        raise self.retry(exc=exc, countdown=60)
