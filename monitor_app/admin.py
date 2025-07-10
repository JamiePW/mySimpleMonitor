from django.contrib import admin
from .models import MonitorStatus

class MonitorStatusAdmin(admin.ModelAdmin):
    list_display = ('object_type', 'object_id', 'is_normal', 'last_status', 'last_changed')
    search_fields = ('object_type', 'object_id')
    list_filter = ('is_normal', 'object_type')

admin.site.register(MonitorStatus, MonitorStatusAdmin)

