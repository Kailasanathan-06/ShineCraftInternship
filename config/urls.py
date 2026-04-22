from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboard.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("assets/", include("apps.assets.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("api/assets/", include("apps.assets.urls")),
]