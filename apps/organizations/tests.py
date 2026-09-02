from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Organization, OrganizationMembership


class OrganizationAPITests(APITestCase):
    def setUp(self):
        self.password = 'test-pass-1234'
        self.user = get_user_model().objects.create_user(
            email='owner@example.com',
            password=self.password,
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_jwt_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {
                'email': self.user.email,
                'password': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_authenticated_user_can_create_organization_and_becomes_owner(self):
        self.authenticate()

        response = self.client.post(
            '/api/v1/organizations/',
            {
                'name': 'Syncora Demo Company',
                'email': 'demo@syncora.local',
                'phone': '01700000000',
                'address': 'Dhaka, Bangladesh',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'syncora-demo-company')

        organization = Organization.objects.get(id=response.data['id'])
        membership = OrganizationMembership.objects.get(
            user=self.user,
            organization=organization,
        )
        self.assertEqual(membership.role, OrganizationMembership.Role.OWNER)
        self.assertTrue(membership.is_owner)
        self.assertTrue(membership.is_admin)
        self.assertTrue(membership.is_manager)

    def test_members_endpoint_lists_organization_memberships(self):
        self.authenticate()
        organization = Organization.objects.create(name='Syncora Demo Company')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )

        response = self.client.get(f'/api/v1/organizations/{organization.id}/members/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_email'], self.user.email)
        self.assertEqual(response.data[0]['role'], OrganizationMembership.Role.OWNER)

    def test_organization_updates_are_broadcast_to_channel_group(self):
        self.authenticate()
        organization = Organization.objects.create(name='Syncora Demo Company')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        channel_layer = Mock()
        sync_group_send = Mock()

        with (
            patch('apps.organizations.views.get_channel_layer', return_value=channel_layer),
            patch('apps.organizations.views.async_to_sync', return_value=sync_group_send),
        ):
            response = self.client.patch(
                f'/api/v1/organizations/{organization.id}/',
                {'name': 'Syncora Live Company'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sync_group_send.assert_called_once()
        self.assertEqual(sync_group_send.call_args.args[0], f'organization_{organization.id}')
        self.assertEqual(sync_group_send.call_args.args[1]['type'], 'organization.updated')
        self.assertEqual(sync_group_send.call_args.args[1]['data']['name'], 'Syncora Live Company')
