from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.organizations.models import Organization, OrganizationMembership

from .models import Customer


class CustomerAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='customer-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Customer Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def test_manager_can_create_customer(self):
        manager = self.create_user('customer-manager@example.com')
        OrganizationMembership.objects.create(
            user=manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.authenticate(manager)

        response = self.client.post(
            '/api/v1/customers/',
            {
                'organization': self.organization.id,
                'name': 'Rahim Uddin',
                'phone': '01700000002',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Customer.objects.filter(name='Rahim Uddin').exists())

    def test_employee_can_read_but_cannot_create_customer(self):
        employee = self.create_user('customer-employee@example.com')
        OrganizationMembership.objects.create(
            user=employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        Customer.objects.create(organization=self.organization, name='Visible Customer')
        self.authenticate(employee)

        list_response = self.client.get('/api/v1/customers/')
        create_response = self.client.post(
            '/api/v1/customers/',
            {'organization': self.organization.id, 'name': 'Blocked Customer'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
