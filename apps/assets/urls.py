from django.urls import path
from .views import asset_list_view, asset_detail_view, ManualScanAPIView, agent_checkin, agent_upload

urlpatterns = [
    path("", asset_list_view, name="asset-list"),
    path("<int:pk>/", asset_detail_view, name="asset-detail"),
    path("scan/", ManualScanAPIView.as_view(), name="manual-scan"), 
    path("agent/checkin/<str:hostname>/", agent_checkin, name="agent-checkin"),
    path("agent/upload/", agent_upload, name="agent-upload"),
]