from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.organizations.models import Organization, OrganizationMembership

from .models import Branch


class BranchAPITests(APITestCase):
    def setUp(self):
        self.password = 'test-pass-1234'
        self.owner = get_user_model().objects.create_user(
            email='branch-owner@example.com',
            password=self.password,
        )
        self.organization = Organization.objects.create(name='Branch Org')
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password=self.password)

    def add_member(self, user, role):
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.owner)

    def test_owner_can_create_branch(self):
        self.authenticate()

        response = self.client.post(
            '/api/v1/branches/',
            {
                'organization': self.organization.id,
                'name': 'Dhaka Central',
                'code': 'DHK',
                'email': 'dhaka@syncora.local',
                'phone': '01700000001',
                'address': 'Dhaka',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'dhaka-central')
        self.assertTrue(
            Branch.objects.filter(
                organization=self.organization,
                name='Dhaka Central',
            ).exists()
        )

    def test_manager_can_create_branch(self):
        manager = self.create_user('branch-manager@example.com')
        self.add_member(manager, OrganizationMembership.Role.MANAGER)
        self.authenticate(manager)

        response = self.client.post(
            '/api/v1/branches/',
            {'organization': self.organization.id, 'name': 'Chittagong', 'code': 'CTG'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_employee_can_read_but_cannot_create_branch(self):
        employee = self.create_user('branch-employee@example.com')
        self.add_member(employee, OrganizationMembership.Role.EMPLOYEE)
        Branch.objects.create(organization=self.organization, name='Dhaka Central')
        self.authenticate(employee)

        list_response = self.client.get('/api/v1/branches/')
        create_response = self.client.post(
            '/api/v1/branches/',
            {'organization': self.organization.id, 'name': 'Blocked Branch', 'code': 'BLOCKED'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), 1)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_cannot_list_organization_branches(self):
        outsider = self.create_user('branch-outsider@example.com')
        Branch.objects.create(organization=self.organization, name='Hidden Branch')
        self.authenticate(outsider)

        response = self.client.get('/api/v1/branches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
