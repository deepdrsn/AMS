from django.contrib import admin

from .models import OfficeSettings


@admin.register(OfficeSettings)
class OfficeSettingsAdmin(admin.ModelAdmin):
    list_display = ('office_name', 'radius_meters', 'updated_at')
    search_fields = ('office_name',)

