"""
Analytics Views - MongoDB Aggregation Queries
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from lms.apps.analytics.cache_service import RedisCacheMonitor

logger = logging.getLogger(__name__)


@login_required
def cache_stats_view(request):
    """Endpoint untuk melihat statistik Redis cache."""
    stats = RedisCacheMonitor.get_cache_stats()
    return JsonResponse(stats)


@login_required
def activity_logs_view(request):
    """
    Ambil activity logs dari MongoDB dengan filter.

    Query params:
    - user_id: filter by user
    - action: filter by action type
    - limit: jumlah hasil (default 50)
    """
    try:
        from lms.apps.analytics.documents import ActivityLog

        user_id = request.GET.get('user_id')
        action = request.GET.get('action')
        limit = int(request.GET.get('limit', 50))

        # Build query
        query = {}
        if user_id:
            query['user_id'] = int(user_id)
        if action:
            query['action'] = action

        logs = ActivityLog.objects(**query).order_by('-timestamp').limit(limit)

        data = [
            {
                'id': str(log.id),
                'user_id': log.user_id,
                'username': log.username,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_name': log.resource_name,
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.isoformat(),
                'metadata': log.metadata,
            }
            for log in logs
        ]

        return JsonResponse({'count': len(data), 'logs': data})

    except Exception as e:
        logger.error(f"Error fetching activity logs: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def aggregations_view(request):
    """
    MongoDB Aggregation Queries untuk analytics report.

    Tersedia aggregations:
    - action_summary: Hitung aktivitas per tipe
    - daily_active_users: DAU per hari (7 hari terakhir)
    - top_courses: Kursus paling banyak diakses
    """
    try:
        from lms.apps.analytics.documents import ActivityLog
        from datetime import datetime, timedelta

        report_type = request.GET.get('type', 'action_summary')

        if report_type == 'action_summary':
            # Aggregation 1: Hitung aktivitas per action type
            pipeline = [
                {'$group': {
                    '_id': '$action',
                    'total_count': {'$sum': 1},
                    'unique_users': {'$addToSet': '$user_id'},
                }},
                {'$project': {
                    'action': '$_id',
                    'total_count': 1,
                    'unique_user_count': {'$size': '$unique_users'},
                    '_id': 0,
                }},
                {'$sort': {'total_count': -1}},
            ]
            results = list(ActivityLog.objects.aggregate(*pipeline))

        elif report_type == 'daily_active_users':
            # Aggregation 2: Daily Active Users - 7 hari terakhir
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            pipeline = [
                {'$match': {'timestamp': {'$gte': seven_days_ago}}},
                {'$group': {
                    '_id': {
                        'year': {'$year': '$timestamp'},
                        'month': {'$month': '$timestamp'},
                        'day': {'$dayOfMonth': '$timestamp'},
                    },
                    'active_users': {'$addToSet': '$user_id'},
                    'total_activities': {'$sum': 1},
                }},
                {'$project': {
                    'date': {
                        '$dateToString': {
                            'format': '%Y-%m-%d',
                            'date': {
                                '$dateFromParts': {
                                    'year': '$_id.year',
                                    'month': '$_id.month',
                                    'day': '$_id.day',
                                }
                            }
                        }
                    },
                    'dau': {'$size': '$active_users'},
                    'total_activities': 1,
                    '_id': 0,
                }},
                {'$sort': {'date': 1}},
            ]
            results = list(ActivityLog.objects.aggregate(*pipeline))

        elif report_type == 'top_courses':
            # Aggregation 3: Top courses berdasarkan views
            pipeline = [
                {'$match': {
                    'resource_type': 'course',
                    'action': {'$in': ['course_view', 'course_enroll']},
                }},
                {'$group': {
                    '_id': {
                        'course_id': '$resource_id',
                        'course_name': '$resource_name',
                    },
                    'total_views': {
                        '$sum': {'$cond': [{'$eq': ['$action', 'course_view']}, 1, 0]}
                    },
                    'total_enrollments': {
                        '$sum': {'$cond': [{'$eq': ['$action', 'course_enroll']}, 1, 0]}
                    },
                    'unique_visitors': {'$addToSet': '$user_id'},
                }},
                {'$project': {
                    'course_id': '$_id.course_id',
                    'course_name': '$_id.course_name',
                    'total_views': 1,
                    'total_enrollments': 1,
                    'unique_visitors': {'$size': '$unique_visitors'},
                    '_id': 0,
                }},
                {'$sort': {'total_views': -1}},
                {'$limit': 10},
            ]
            results = list(ActivityLog.objects.aggregate(*pipeline))

        else:
            return JsonResponse({'error': 'Unknown report type'}, status=400)

        return JsonResponse({
            'report_type': report_type,
            'count': len(results),
            'data': results,
        })

    except Exception as e:
        logger.error(f"Aggregation error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
