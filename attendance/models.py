from django.conf import settings
from django.db import models


class DeviceLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_agent = models.CharField(max_length=512, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Light fingerprint (client-side hash) to detect suspicious multi-device usage
    device_fingerprint = models.CharField(max_length=128, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DeviceLog({self.user_id}) @ {self.created_at:%Y-%m-%d %H:%M}" 


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        LATE = 'late', 'Late'

    intern = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()

    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    is_late = models.BooleanField(default=False)
    is_on_break = models.BooleanField(default=False)

    # Stored for convenience; can also be computed from times
    total_working_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_break_minutes = models.PositiveIntegerField(default=0)

    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('intern', 'date')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['intern', 'date']),
        ]

    def __str__(self):
        return f"Attendance({self.intern_id}, {self.date})"


class BreakLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='breaks')
    date = models.DateField()
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    duration_minutes = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"BreakLog({self.user_id}, {self.date})"

    @property
    def is_active(self):
        return self.end_time is None
