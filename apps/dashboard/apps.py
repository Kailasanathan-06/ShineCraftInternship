from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'

    def ready(self):
        """Initialize the auto-scan scheduler when Django starts"""
        try:
            from agent.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            print(f"[Dashboard] Failed to start scheduler: {str(e)}")
