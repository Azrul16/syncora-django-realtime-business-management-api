from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.organizations.models import OrganizationMembership

from ..event_types import EventType, build_realtime_event
from ..models import ActivityLog, Notification


def get_resource_identity(resource):
    if not resource:
        return '', ''
    return resource.__class__.__name__, str(resource.pk)


def get_default_recipients(organization):
    return [
        membership.user
        for membership in OrganizationMembership.objects.select_related('user').filter(
            organization=organization,
            is_active=True,
        )
    ]


def dispatch_event(
    *,
    event,
    organization,
    actor=None,
    resource=None,
    data=None,
    branch=None,
    recipients=None,
    notification_title='',
    notification_message='',
    activity_description='',
    activity_metadata=None,
    groups=None,
):
    data = data or {}
    resource_type, resource_id = get_resource_identity(resource)

    activity = ActivityLog.objects.create(
        organization=organization,
        branch=branch,
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        action=event,
        resource_type=resource_type,
        resource_id=resource_id,
        description=activity_description,
        metadata=activity_metadata or data,
    )

    if recipients is None:
        recipients = get_default_recipients(organization)

    notifications = []
    if notification_title:
        notifications = [
            Notification(
                organization=organization,
                recipient=recipient,
                type=event,
                title=notification_title,
                message=notification_message,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            for recipient in recipients
        ]
        notifications = Notification.objects.bulk_create(notifications)

    payload = build_realtime_event(
        event,
        organization.id,
        {
            **data,
            'activity_id': activity.id,
            'resource_type': resource_type,
            'resource_id': resource_id,
        },
    )

    channel_layer = get_channel_layer()
    if channel_layer:
        websocket_groups = set(groups or [])
        websocket_groups.add(f'organization_{organization.id}')
        if branch:
            websocket_groups.add(f'organization_{organization.id}_branch_{branch.id}')

        for group_name in websocket_groups:
            async_to_sync(channel_layer.group_send)(group_name, payload)

        for notification in notifications:
            async_to_sync(channel_layer.group_send)(
                f'user_{notification.recipient_id}_notifications',
                build_realtime_event(
                    EventType.NOTIFICATION_CREATED,
                    organization.id,
                    {
                        'notification_id': notification.id,
                        'type': notification.type,
                        'title': notification.title,
                        'message': notification.message,
                        'is_read': notification.is_read,
                    },
                ),
            )

    return activity
