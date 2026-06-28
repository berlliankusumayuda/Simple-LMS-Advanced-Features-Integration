"""
MongoDB Document Models menggunakan MongoEngine
Untuk Activity Logs dan Learning Analytics
"""
import mongoengine as me
from datetime import datetime


# ============================================================
# ACTIVITY LOG COLLECTION
# ============================================================
class ActivityLog(me.Document):
    """
    Menyimpan semua aktivitas user di LMS.
    Digunakan untuk audit trail dan analytics.
    """
    # User info
    user_id = me.IntField(required=True)
    username = me.StringField(required=True, max_length=150)

    # Action details
    action = me.StringField(required=True, choices=[
        'login', 'logout',
        'course_view', 'course_enroll', 'course_complete',
        'lesson_start', 'lesson_complete',
        'quiz_attempt', 'quiz_pass', 'quiz_fail',
        'certificate_download', 'report_export',
    ])
    resource_type = me.StringField(choices=['course', 'lesson', 'quiz', 'certificate', 'user'])
    resource_id = me.IntField()
    resource_name = me.StringField()

    # Request metadata
    ip_address = me.StringField(max_length=45)
    user_agent = me.StringField()
    method = me.StringField(max_length=10)
    path = me.StringField()

    # Additional context
    metadata = me.DictField()  # flexible extra data
    timestamp = me.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'activity_logs',
        'indexes': [
            'user_id',
            'action',
            'resource_type',
            '-timestamp',
            {'fields': ['user_id', '-timestamp']},
            {'fields': ['resource_type', 'resource_id', '-timestamp']},
        ],
        'ordering': ['-timestamp'],
    }

    def __str__(self):
        return f"[{self.timestamp}] {self.username}: {self.action}"


# ============================================================
# LEARNING ANALYTICS COLLECTION
# ============================================================
class LearningSession(me.Document):
    """
    Menyimpan data session belajar user untuk analytics.
    """
    user_id = me.IntField(required=True)
    course_id = me.IntField(required=True)
    lesson_id = me.IntField()

    started_at = me.DateTimeField(required=True)
    ended_at = me.DateTimeField()
    duration_seconds = me.IntField(default=0)

    # Progress tracking
    progress_before = me.FloatField(default=0.0)
    progress_after = me.FloatField(default=0.0)

    # Engagement metrics
    interactions = me.IntField(default=0)  # clicks, scrolls, etc.
    video_watched_seconds = me.IntField(default=0)

    meta = {
        'collection': 'learning_sessions',
        'indexes': [
            'user_id',
            'course_id',
            '-started_at',
            {'fields': ['user_id', 'course_id']},
        ],
    }


class CourseAnalytics(me.Document):
    """
    Agregasi data analytics per course.
    Diupdate secara berkala oleh Celery tasks.
    """
    course_id = me.IntField(required=True, unique=True)
    course_title = me.StringField()

    # Enrollment stats
    total_enrollments = me.IntField(default=0)
    active_students = me.IntField(default=0)
    completed_students = me.IntField(default=0)
    dropped_students = me.IntField(default=0)
    completion_rate = me.FloatField(default=0.0)

    # Engagement stats
    avg_progress = me.FloatField(default=0.0)
    avg_session_duration = me.FloatField(default=0.0)
    total_learning_hours = me.FloatField(default=0.0)

    # Time-based data
    enrollments_by_month = me.DictField()  # {"2024-01": 25, "2024-02": 30}
    daily_active_users = me.DictField()    # {"2024-01-15": 10}

    last_updated = me.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'course_analytics',
        'indexes': [
            'course_id',
            '-total_enrollments',
            '-completion_rate',
        ],
    }


class QuizAnalytics(me.Document):
    """
    Analytics untuk quiz dan assessment.
    """
    quiz_id = me.IntField(required=True)
    course_id = me.IntField(required=True)
    user_id = me.IntField(required=True)

    attempt_number = me.IntField(default=1)
    score = me.FloatField(required=True)
    max_score = me.FloatField(required=True)
    passed = me.BooleanField(default=False)

    answers = me.ListField(me.DictField())  # [{question_id, answer, correct}]
    time_taken_seconds = me.IntField(default=0)

    attempted_at = me.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'quiz_analytics',
        'indexes': [
            'user_id',
            'quiz_id',
            'course_id',
            '-attempted_at',
        ],
    }
