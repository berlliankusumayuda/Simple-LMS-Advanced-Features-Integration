"""
Course API Views dengan Redis Caching Integration
"""
import logging
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from lms.apps.courses.models import Course, Enrollment
from lms.apps.analytics.cache_service import CacheService

logger = logging.getLogger(__name__)


class CourseSerializer:
    """Simplified serializer - implementasi lengkap di production."""
    @staticmethod
    def serialize(course, detail=False):
        data = {
            'id': course.id,
            'title': course.title,
            'slug': course.slug,
            'description': course.description,
            'instructor': {
                'id': course.instructor.id,
                'name': course.instructor.get_full_name(),
                'username': course.instructor.username,
            },
            'category': course.category.name if course.category else None,
            'price': str(course.price),
            'enrollment_count': course.enrollment_count,
            'status': course.status,
            'created_at': course.created_at.isoformat(),
        }
        if detail:
            data['lessons'] = [
                {
                    'id': l.id,
                    'title': l.title,
                    'order': l.order,
                    'duration_minutes': l.duration_minutes,
                }
                for l in course.lessons.all().order_by('order')
            ]
        return data


class CourseViewSet(viewsets.ViewSet):
    """
    ViewSet untuk Course API dengan Redis caching.

    Endpoints:
    - GET /api/courses/          - List dengan caching
    - GET /api/courses/{id}/     - Detail dengan caching
    - POST /api/courses/         - Create (invalidate list cache)
    - PUT /api/courses/{id}/     - Update (invalidate detail + list cache)
    - POST /api/courses/{id}/enroll/ - Enroll + trigger Celery tasks
    - GET /api/courses/{id}/report/  - Export report async
    - GET /api/courses/{id}/stats/   - Statistics dengan caching
    """

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    # ----------------------------------------------------------
    # LIST - dengan Redis caching
    # ----------------------------------------------------------
    def list(self, request):
        """
        Ambil daftar kursus dengan caching.
        Cache key: courses:list:{page}:{page_size}:{search}:{category}:{status}
        TTL: 5 menit
        """
        # Parse query params
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        search = request.query_params.get('search', '')
        category = request.query_params.get('category', '')
        status_filter = request.query_params.get('status', 'published')

        # Cek cache terlebih dahulu
        cached_data = CacheService.get_cached_course_list(
            page=page, page_size=page_size,
            search=search, category=category, status=status_filter
        )

        if cached_data is not None:
            cached_data['from_cache'] = True
            return Response(cached_data)

        # Cache MISS - query database
        queryset = Course.objects.filter(status=status_filter).select_related(
            'instructor', 'category'
        )

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(instructor__username__icontains=search)
            )

        if category:
            queryset = queryset.filter(category__slug=category)

        # Pagination
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        courses = queryset[start:end]

        data = {
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'from_cache': False,
            'results': [CourseSerializer.serialize(c) for c in courses],
        }

        # Simpan ke cache
        CacheService.set_cached_course_list(
            data, page=page, page_size=page_size,
            search=search, category=category, status=status_filter
        )

        return Response(data)

    # ----------------------------------------------------------
    # RETRIEVE - dengan Redis caching
    # ----------------------------------------------------------
    def retrieve(self, request, pk=None):
        """
        Ambil detail kursus dengan caching.
        Cache key: courses:detail:{course_id}
        TTL: 10 menit
        """
        # Cek cache
        cached_data = CacheService.get_cached_course_detail(pk)
        if cached_data is not None:
            cached_data['from_cache'] = True
            return Response(cached_data)

        # Cache MISS - query database
        try:
            course = Course.objects.select_related(
                'instructor', 'category'
            ).prefetch_related('lessons').get(id=pk)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=404)

        data = CourseSerializer.serialize(course, detail=True)
        data['from_cache'] = False

        # Simpan ke cache
        CacheService.set_cached_course_detail(pk, data)

        return Response(data)

    # ----------------------------------------------------------
    # CREATE - invalidate list cache
    # ----------------------------------------------------------
    def create(self, request):
        """Buat course baru dan invalidate course list cache."""
        # ... validasi dan save ...
        course = Course.objects.create(
            title=request.data.get('title', ''),
            description=request.data.get('description', ''),
            instructor=request.user,
            slug=request.data.get('slug', ''),
        )

        # Invalidate list cache karena ada course baru
        CacheService.invalidate_course_list_cache()
        logger.info(f"Course {course.id} created - list cache invalidated")

        return Response(CourseSerializer.serialize(course), status=201)

    # ----------------------------------------------------------
    # UPDATE - invalidate detail + list cache
    # ----------------------------------------------------------
    def update(self, request, pk=None):
        """Update course dan invalidate caches terkait."""
        try:
            course = Course.objects.get(id=pk, instructor=request.user)
        except Course.DoesNotExist:
            return Response({'error': 'Not found or unauthorized'}, status=404)

        # Update fields
        for field in ['title', 'description', 'status']:
            if field in request.data:
                setattr(course, field, request.data[field])
        course.save()

        # Invalidate semua cache terkait course ini
        CacheService.invalidate_course_cache(pk)
        logger.info(f"Course {pk} updated - caches invalidated")

        return Response(CourseSerializer.serialize(course))

    # ----------------------------------------------------------
    # ENROLL - trigger Celery tasks
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='enroll')
    def enroll(self, request, pk=None):
        """
        Enroll student ke course.
        Trigger Celery tasks:
        1. send_enrollment_email (async)
        2. Invalidate course cache
        """
        try:
            course = Course.objects.get(id=pk, status='published')
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=404)

        # Cek sudah enrolled
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return Response({'error': 'Sudah terdaftar di kursus ini'}, status=400)

        # Buat enrollment
        enrollment = Enrollment.objects.create(
            student=request.user,
            course=course,
            status='active',
        )

        # Update enrollment count di course
        Course.objects.filter(id=pk).update(
            enrollment_count=course.enrollment_count + 1
        )

        # Invalidate cache
        CacheService.invalidate_course_cache(pk)

        # Trigger async tasks
        from lms.tasks.course_tasks import send_enrollment_email
        task = send_enrollment_email.delay(enrollment.id)

        logger.info(
            f"Enrollment created: student={request.user.username}, "
            f"course={course.title}, task_id={task.id}"
        )

        return Response({
            'message': 'Berhasil mendaftar!',
            'enrollment_id': enrollment.id,
            'course': course.title,
            'email_task_id': task.id,
        }, status=201)

    # ----------------------------------------------------------
    # REPORT EXPORT - async Celery task
    # ----------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='report')
    def export_report(self, request, pk=None):
        """
        Export course report secara asynchronous.
        Response langsung dengan task_id, file dikirim via email.
        """
        report_format = request.data.get('format', 'csv')

        from lms.tasks.course_tasks import export_course_report
        task = export_course_report.delay(
            course_id=pk,
            requested_by_user_id=request.user.id,
            report_format=report_format,
        )

        return Response({
            'message': 'Report sedang diproses. Anda akan mendapat email saat selesai.',
            'task_id': task.id,
            'format': report_format,
        }, status=202)

    # ----------------------------------------------------------
    # STATISTICS - dengan caching
    # ----------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='stats')
    def statistics(self, request, pk=None):
        """
        Ambil statistik course dari MongoDB analytics dengan caching.
        Cache TTL: 30 menit
        """
        cached_stats = CacheService.get_cached_course_statistics(pk)
        if cached_stats:
            cached_stats['from_cache'] = True
            return Response(cached_stats)

        try:
            from lms.apps.analytics.documents import CourseAnalytics
            analytics = CourseAnalytics.objects.get(course_id=int(pk))
            stats = {
                'course_id': analytics.course_id,
                'course_title': analytics.course_title,
                'total_enrollments': analytics.total_enrollments,
                'active_students': analytics.active_students,
                'completed_students': analytics.completed_students,
                'completion_rate': analytics.completion_rate,
                'avg_progress': analytics.avg_progress,
                'last_updated': analytics.last_updated.isoformat(),
                'from_cache': False,
            }
        except Exception:
            # Fallback ke PostgreSQL jika MongoDB belum ada data
            course = Course.objects.get(id=pk)
            stats = {
                'course_id': int(pk),
                'total_enrollments': course.enrollment_count,
                'from_cache': False,
                'note': 'Analytics belum tersedia, menampilkan data dasar'
            }

        CacheService.set_cached_course_statistics(pk, stats)
        return Response(stats)
