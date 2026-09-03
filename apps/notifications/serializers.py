from rest_framework import serializers

from .models import Notification


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

