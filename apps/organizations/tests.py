from unittest.mock import Mock, patch

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITransactionTestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
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

    def test_owner_can_add_existing_user_as_member(self):
        self.authenticate()
        organization = self.create_organization_with_membership()
        employee = self.create_user('new-employee@example.com')

        response = self.client.post(
            f'/api/v1/organizations/{organization.id}/members/',
            {
                'user_email': employee.email,
                'role': OrganizationMembership.Role.EMPLOYEE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_email'], employee.email)
        self.assertEqual(response.data['role'], OrganizationMembership.Role.EMPLOYEE)
        self.assertTrue(
            OrganizationMembership.objects.filter(
                user=employee,
                organization=organization,
                role=OrganizationMembership.Role.EMPLOYEE,
                is_active=True,
            ).exists()
        )

    def test_manager_cannot_add_members(self):
        manager = self.create_user('member-manager@example.com')
        new_member = self.create_user('blocked-employee@example.com')
        organization = self.create_organization_with_membership(
            user=manager,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.client.force_authenticate(user=manager)

        response = self.client.post(
            f'/api/v1/organizations/{organization.id}/members/',
            {
                'user_email': new_member.email,
                'role': OrganizationMembership.Role.EMPLOYEE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            OrganizationMembership.objects.filter(
                user=new_member,
                organization=organization,
            ).exists()
        )

    def test_admin_can_update_non_owner_member_role(self):
        admin = self.create_user('role-admin@example.com')
        employee = self.create_user('role-employee@example.com')
        organization = self.create_organization_with_membership(
            user=admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        membership = OrganizationMembership.objects.create(
            user=employee,
            organization=organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        self.client.force_authenticate(user=admin)

        response = self.client.patch(
            f'/api/v1/organizations/{organization.id}/members/{membership.id}/',
            {'role': OrganizationMembership.Role.MANAGER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership.refresh_from_db()
        self.assertEqual(membership.role, OrganizationMembership.Role.MANAGER)

    def test_admin_cannot_assign_owner_role(self):
        admin = self.create_user('limited-admin@example.com')
        employee = self.create_user('future-owner@example.com')
        organization = self.create_organization_with_membership(
            user=admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        membership = OrganizationMembership.objects.create(
            user=employee,
            organization=organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        self.client.force_authenticate(user=admin)

        response = self.client.patch(
            f'/api/v1/organizations/{organization.id}/members/{membership.id}/',
            {'role': OrganizationMembership.Role.OWNER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        membership.refresh_from_db()
        self.assertEqual(membership.role, OrganizationMembership.Role.EMPLOYEE)

    def test_owner_can_deactivate_member(self):
        self.authenticate()
        employee = self.create_user('inactive-employee@example.com')
        organization = self.create_organization_with_membership()
        membership = OrganizationMembership.objects.create(
            user=employee,
            organization=organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )

        response = self.client.delete(
            f'/api/v1/organizations/{organization.id}/members/{membership.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)

    def test_member_cannot_manage_own_membership(self):
        self.authenticate()
        organization = self.create_organization_with_membership()
        membership = OrganizationMembership.objects.get(
            user=self.user,
            organization=organization,
        )

        response = self.client.patch(
            f'/api/v1/organizations/{organization.id}/members/{membership.id}/',
            {'is_active': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        membership.refresh_from_db()
        self.assertTrue(membership.is_active)


class OrganizationWebSocketTests(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='socket-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Realtime Company')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )

    def access_token_for(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    async def connect(self, path):
        communicator = WebsocketCommunicator(application, path)
        connected, close_code = await communicator.connect()
        return communicator, connected, close_code

    def test_member_with_valid_token_can_connect_to_organization_socket(self):
        token = self.access_token_for(self.user)

        async def connect_and_receive():
            communicator, connected, close_code = await self.connect(
                f'/ws/organizations/{self.organization.id}/?token={token}'
            )
            message = await communicator.receive_json_from()
            await communicator.disconnect()
            return connected, close_code, message

        connected, _, message = async_to_sync(connect_and_receive)()

        self.assertTrue(connected)
        self.assertEqual(message['type'], 'connection.ready')

    def test_socket_rejects_missing_token(self):
        async def connect():
            _, connected, close_code = await self.connect(
                f'/ws/organizations/{self.organization.id}/'
            )
            return connected, close_code

        connected, close_code = async_to_sync(connect)()

        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    def test_socket_rejects_non_member_token(self):
        outsider = get_user_model().objects.create_user(
            email='socket-outsider@example.com',
            password='test-pass-1234',
        )
        token = self.access_token_for(outsider)

        async def connect():
            _, connected, close_code = await self.connect(
                f'/ws/organizations/{self.organization.id}/?token={token}'
            )
            return connected, close_code

        connected, close_code = async_to_sync(connect)()

        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)
