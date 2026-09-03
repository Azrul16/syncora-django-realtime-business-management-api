from django.contrib import admin

from .models import ActivityLog, AuditLog, Notification


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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'organization', 'actor', 'target_type', 'target_id', 'ip_address', 'created_at')
    list_filter = ('action', 'organization', 'created_at')
    search_fields = ('action', 'actor__email', 'target_type', 'target_id', 'request_id')
    readonly_fields = [field.name for field in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
