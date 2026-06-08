from django.contrib import admin
from .models import Attendance, BreakLog, DeviceLog


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('intern', 'date', 'check_in_time', 'check_out_time', 'status', 'is_late', 'total_working_hours', 'total_break_minutes')
    list_filter = ('date', 'status', 'is_late')
    search_fields = ('intern__username', 'intern__email')
    ordering = ('-date',)


@admin.register(BreakLog)
class BreakLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'start_time', 'end_time', 'duration_minutes', 'is_active')
    list_filter = ('date', 'user')
    search_fields = ('user__username', 'user__email')
    ordering = ('-date', '-start_time')


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'device_fingerprint', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'ip_address')
    ordering = ('-created_at',)
