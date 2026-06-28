from django.apps import AppConfig

class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lms.apps.analytics'
    verbose_name = 'Analytics'

    def ready(self):
        import mongoengine
        from django.conf import settings
        try:
            mongoengine.connect(host=settings.MONGODB_URI)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"MongoDB connection warning: {e}")
