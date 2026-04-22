from django.urls import path
from .views import dashboard_home, ScheduleAutoScanAPIView

urlpatterns = [
    path("", dashboard_home, name="dashboard-home"),
    path("api/schedule-scan/", ScheduleAutoScanAPIView.as_view(), name="schedule-scan"),
]