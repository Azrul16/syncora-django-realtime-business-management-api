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

    def create_user(self, email):
        return get_user_model().objects.create_user(
            email=email,
            password=self.password,
        )

    def create_organization_with_membership(self, user=None, role=None):
        user = user or self.user
        role = role or OrganizationMembership.Role.OWNER
        organization = Organization.objects.create(name='Syncora Demo Company')
        OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role=role,
        )
        return organization

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
        organization = self.create_organization_with_membership()

        response = self.client.get(f'/api/v1/organizations/{organization.id}/members/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_email'], self.user.email)
        self.assertEqual(response.data[0]['role'], OrganizationMembership.Role.OWNER)

    def test_organization_updates_are_broadcast_to_channel_group(self):
        self.authenticate()
        organization = self.create_organization_with_membership()
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

    def test_admin_member_can_update_organization(self):
        admin_user = self.create_user('admin@example.com')
        organization = self.create_organization_with_membership(
            user=admin_user,
            role=OrganizationMembership.Role.ADMIN,
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.patch(
            f'/api/v1/organizations/{organization.id}/',
            {'name': 'Updated by Admin'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization.refresh_from_db()
        self.assertEqual(organization.name, 'Updated by Admin')

    def test_manager_member_can_read_but_cannot_update_organization(self):
        manager_user = self.create_user('manager@example.com')
        organization = self.create_organization_with_membership(
            user=manager_user,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.client.force_authenticate(user=manager_user)

        read_response = self.client.get(f'/api/v1/organizations/{organization.id}/')
        update_response = self.client.patch(
            f'/api/v1/organizations/{organization.id}/',
            {'name': 'Updated by Manager'},
            format='json',
        )

        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        organization.refresh_from_db()
        self.assertEqual(organization.name, 'Syncora Demo Company')

    def test_employee_member_can_read_but_cannot_update_organization(self):
        employee_user = self.create_user('employee@example.com')
        organization = self.create_organization_with_membership(
            user=employee_user,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        self.client.force_authenticate(user=employee_user)

        read_response = self.client.get(f'/api/v1/organizations/{organization.id}/')
        update_response = self.client.patch(
            f'/api/v1/organizations/{organization.id}/',
            {'name': 'Updated by Employee'},
            format='json',
        )

        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        organization.refresh_from_db()
        self.assertEqual(organization.name, 'Syncora Demo Company')

    def test_non_member_cannot_view_or_update_organization(self):
        organization = self.create_organization_with_membership()
        outsider = self.create_user('outsider@example.com')
        self.client.force_authenticate(user=outsider)

        read_response = self.client.get(f'/api/v1/organizations/{organization.id}/')
        update_response = self.client.patch(
            f'/api/v1/organizations/{organization.id}/',
            {'name': 'Updated by Outsider'},
            format='json',
        )

        self.assertEqual(read_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)
        organization.refresh_from_db()
        self.assertEqual(organization.name, 'Syncora Demo Company')
