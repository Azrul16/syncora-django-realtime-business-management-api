from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.organizations.models import Organization, OrganizationMembership

from .models import Product


class ProductAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='product-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Product Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def test_manager_can_create_product(self):
        manager = self.create_user('product-manager@example.com')
        OrganizationMembership.objects.create(
            user=manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.authenticate(manager)

        response = self.client.post(
            '/api/v1/products/',
            {
                'organization': self.organization.id,
                'name': 'Paracetamol 500mg',
                'sku': 'MED-PARA-500',
                'unit': 'box',
                'cost_price': '80.00',
                'selling_price': '120.00',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'paracetamol-500mg')

    def test_employee_can_read_but_cannot_create_product(self):
        employee = self.create_user('product-employee@example.com')
        OrganizationMembership.objects.create(
            user=employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        Product.objects.create(
            organization=self.organization,
            name='Visible Product',
            sku='VISIBLE-1',
        )
        self.authenticate(employee)

        list_response = self.client.get('/api/v1/products/')
        create_response = self.client.post(
            '/api/v1/products/',
            {'organization': self.organization.id, 'name': 'Blocked Product', 'sku': 'BLOCKED-1'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_cannot_list_products(self):
        outsider = self.create_user('product-outsider@example.com')
        Product.objects.create(
            organization=self.organization,
            name='Hidden Product',
            sku='HIDDEN-1',
        )
        self.authenticate(outsider)

        response = self.client.get('/api/v1/products/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
