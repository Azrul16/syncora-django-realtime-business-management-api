from rest_framework import serializers

from .models import ActivityLog, Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'organization',
            'recipient',
            'type',
            'title',
            'message',
            'resource_type',
            'resource_id',
            'is_read',
            'created_at',
            'read_at',
        ]
        read_only_fields = fields


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'organization',
            'branch',
            'actor',
            'actor_email',
            'action',
            'resource_type',
            'resource_id',
            'description',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields
