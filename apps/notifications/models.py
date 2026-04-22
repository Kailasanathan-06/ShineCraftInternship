from django.db import models
from ShineCraftInternship.apps.assets.models import Asset

class ChangeNotification(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=255)
    old_value = models.TextField(null=True)
    new_value = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)