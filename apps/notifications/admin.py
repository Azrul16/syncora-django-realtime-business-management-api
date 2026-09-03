from django.contrib import admin

from .models import ActivityLog, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'organization', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'organization', 'created_at')
    search_fields = ('title', 'message', 'recipient__email', 'organization__name')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'organization', 'branch', 'actor', 'resource_type', 'resource_id', 'created_at')
    list_filter = ('action', 'organization', 'branch', 'created_at')
    search_fields = ('action', 'description', 'actor__email', 'organization__name')
