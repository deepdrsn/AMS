from django.conf import settings
from django.db import models


class OfficeSettings(models.Model):
    office_name = models.CharField(max_length=200, default='Main Office')
    office_latitude = models.FloatField()
    office_longitude = models.FloatField()
    radius_meters = models.PositiveIntegerField(default=getattr(settings, 'OFFICE_RADIUS_METERS_DEFAULT', 100))

    # Optional: best-effort office Wi-Fi / IP range validation
    # Store as comma-separated CIDR strings, e.g. "192.168.1.0/24,10.0.0.0/8"
    allowed_wifi_cidrs = models.TextField(blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.office_name} ({self.radius_meters}m)"
