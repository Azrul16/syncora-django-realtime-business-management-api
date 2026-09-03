from unittest.mock import Mock, patch
from urllib.parse import quote

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.organizations.models import Organization, OrganizationMembership

from .event_types import EventType
from .models import ActivityLog, Notification
from .services.event_dispatcher import dispatch_event


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='notify-owner@example.com',
            password='test-pass-1234',
        )
        self.other_user = get_user_model().objects.create_user(
            email='notify-other@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Notification Org')
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            user=self.other_user,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_notification(self, recipient=None, is_read=False):
        return Notification.objects.create(
            organization=self.organization,
            recipient=recipient or self.user,
            type=EventType.SALE_COMPLETED,
            title='Sale completed',
            message='SL-000031 was completed.',
            resource_type='Sale',
            resource_id='31',
            is_read=is_read,
        )

    def test_notification_isolation_between_recipients(self):
        notification = self.create_notification(recipient=self.user)
        self.authenticate(self.other_user)

        response = self.client.get(f'/api/v1/notifications/{notification.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unread_count_tracks_only_unread_notifications(self):
        for _ in range(3):
            self.create_notification()
        for _ in range(2):
            self.create_notification(is_read=True)
        self.authenticate()

        response = self.client.get('/api/v1/notifications/unread-count/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 3)

    def test_mark_one_and_all_notifications_read(self):
        first = self.create_notification()
        self.create_notification()
        self.create_notification()
        self.authenticate()

        read_response = self.client.post(f'/api/v1/notifications/{first.id}/read/')
        count_response = self.client.get('/api/v1/notifications/unread-count/')
        read_all_response = self.client.post('/api/v1/notifications/read-all/')
        final_count_response = self.client.get('/api/v1/notifications/unread-count/')

        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertTrue(read_response.data['is_read'])
        self.assertEqual(count_response.data['unread_count'], 2)
        self.assertEqual(read_all_response.data['updated_count'], 2)
        self.assertEqual(final_count_response.data['unread_count'], 0)

    def test_dispatch_event_creates_activity_log_and_notifications(self):
        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=Mock()):
            dispatch_event(
                event=EventType.SALE_COMPLETED,
                organization=self.organization,
                actor=self.user,
                branch=self.branch,
                data={'sale_number': 'SL-000031', 'total': '85000.00'},
                groups=[f'organization_{self.organization.id}_sales'],
                notification_title='Sale completed',
                notification_message='SL-000031 was completed.',
            )

        activity = ActivityLog.objects.get(action=EventType.SALE_COMPLETED)
        self.assertEqual(activity.organization, self.organization)
        self.assertEqual(activity.actor, self.user)
        self.assertEqual(activity.metadata['sale_number'], 'SL-000031')
        self.assertEqual(Notification.objects.filter(type=EventType.SALE_COMPLETED).count(), 2)

    def test_dispatch_event_uses_scoped_websocket_groups_without_other_tenant(self):
        other_organization = Organization.objects.create(name='Other Notification Org')
        sync_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=sync_group_send):
            dispatch_event(
                event=EventType.PAYMENT_CREATED,
                organization=self.organization,
                actor=self.user,
                branch=self.branch,
                data={'amount': '500.00'},
                groups=[f'organization_{self.organization.id}_payments'],
            )

        groups = {call.args[0] for call in sync_group_send.call_args_list}
        self.assertIn(f'organization_{self.organization.id}', groups)
        self.assertIn(f'organization_{self.organization.id}_payments', groups)
        self.assertIn(f'organization_{self.organization.id}_branch_{self.branch.id}', groups)
        self.assertNotIn(f'organization_{other_organization.id}', groups)

    def test_activity_recovery_after_timestamp_returns_missed_events(self):
        first = ActivityLog.objects.create(
            organization=self.organization,
            actor=self.user,
            action='sale.completed',
            description='First event',
        )
        second = ActivityLog.objects.create(
            organization=self.organization,
            actor=self.user,
            action='payment.created',
            description='Second event',
        )
        self.authenticate()

        response = self.client.get(f'/api/v1/activities/?after={quote(first.created_at.isoformat())}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], second.id)
