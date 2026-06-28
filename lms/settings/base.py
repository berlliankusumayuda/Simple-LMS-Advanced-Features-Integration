"""
LMS Base Settings - Django Configuration
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
]

LOCAL_APPS = [
    'lms.apps.courses',
    'lms.apps.users',
    'lms.apps.analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'lms.middleware.rate_limiter.RateLimitMiddleware',
    'lms.middleware.activity_logger.ActivityLoggerMiddleware',
]

ROOT_URLCONF = 'lms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lms.wsgi.application'

# ============================================================
# DATABASE - PostgreSQL
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='lms_db'),
        'USER': config('POSTGRES_USER', default='lms_user'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='lms_password'),
        'HOST': config('POSTGRES_HOST', default='db'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    }
}

# ============================================================
# REDIS CACHE CONFIGURATION
# ============================================================
REDIS_HOST = config('REDIS_HOST', default='redis')
REDIS_PORT = config('REDIS_PORT', default='6379')
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"{REDIS_URL}/0",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'MAX_CONNECTIONS': 1000,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'lms',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'rate_limit': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"{REDIS_URL}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'ratelimit',
        'TIMEOUT': 60,
    }
}

# Cache timeouts (seconds)
CACHE_TIMEOUTS = {
    'course_list': 300,        # 5 minutes
    'course_detail': 600,      # 10 minutes
    'course_statistics': 1800, # 30 minutes
    'user_profile': 300,       # 5 minutes
}

# Cache keys
CACHE_KEYS = {
    'course_list': 'courses:list:{page}:{page_size}:{search}',
    'course_detail': 'courses:detail:{course_id}',
    'course_statistics': 'courses:stats:{course_id}',
    'enrollment_count': 'courses:enrollment_count:{course_id}',
}

# ============================================================
# MONGODB CONFIGURATION
# ============================================================
MONGODB_HOST = config('MONGODB_HOST', default='mongodb')
MONGODB_PORT = config('MONGODB_PORT', default='27017', cast=int)
MONGODB_DB = config('MONGODB_DB', default='lms_analytics')

MONGODB_URI = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/{MONGODB_DB}"

# ============================================================
# CELERY CONFIGURATION
# ============================================================
RABBITMQ_HOST = config('RABBITMQ_HOST', default='rabbitmq')
RABBITMQ_PORT = config('RABBITMQ_PORT', default='5672')
RABBITMQ_USER = config('RABBITMQ_USER', default='lms_user')
RABBITMQ_PASS = config('RABBITMQ_PASS', default='lms_password')
RABBITMQ_VHOST = config('RABBITMQ_VHOST', default='lms_vhost')

CELERY_BROKER_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/2"
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Jakarta'

# Celery Beat Schedule (for periodic tasks)
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'update-course-statistics': {
        'task': 'lms.tasks.course_tasks.update_course_statistics',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}

# ============================================================
# RATE LIMITING
# ============================================================
RATE_LIMIT_REQUESTS = config('RATE_LIMIT_REQUESTS', default=60, cast=int)
RATE_LIMIT_WINDOW = config('RATE_LIMIT_WINDOW', default=60, cast=int)  # seconds

# ============================================================
# EMAIL CONFIGURATION
# ============================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@lms.com')

# ============================================================
# REST FRAMEWORK
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# ============================================================
# STATIC & MEDIA FILES
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LANGUAGE_CODE = 'id-id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
