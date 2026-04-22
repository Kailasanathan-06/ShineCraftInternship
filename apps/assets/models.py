from django.db import models

class Asset(models.Model):
    hostname = models.CharField(max_length=255, unique=True)
    service_tag = models.CharField(max_length=255, blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    assigned_user = models.CharField(max_length=255, blank=True)
    site_name = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, default="Available")
    last_scan = models.DateTimeField(auto_now=True)
    scan_requested = models.BooleanField(default=False)
    last_checkin = models.DateTimeField(null=True, blank=True)

    @property
    def is_online(self):
        from django.utils import timezone
        import datetime
        if not self.last_checkin:
            return False
        return timezone.now() - self.last_checkin < datetime.timedelta(minutes=5)

    def __str__(self):
        return self.hostname


class ScanResult(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    raw_output = models.JSONField()
    scan_status = models.CharField(max_length=50, default="Completed")
    created_at = models.DateTimeField(auto_now_add=True)