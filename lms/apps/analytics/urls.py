from django.urls import path
from lms.apps.analytics import views

urlpatterns = [
    path('cache-stats/', views.cache_stats_view, name='cache_stats'),
    path('activity-logs/', views.activity_logs_view, name='activity_logs'),
    path('aggregations/', views.aggregations_view, name='aggregations'),
]
