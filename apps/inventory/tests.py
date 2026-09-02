from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product

from .models import InventoryStock


class InventoryStockAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='stock-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Stock Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Paracetamol',
            sku='PARA-1',
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def test_manager_can_create_stock_record(self):
        manager = self.create_user('stock-manager@example.com')
        OrganizationMembership.objects.create(
            user=manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.authenticate(manager)

        response = self.client.post(
            '/api/v1/inventory-stocks/',
            {
                'branch': self.branch.id,
                'product': self.product.id,
                'quantity': '10.00',
                'reorder_level': '5.00',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['organization'], self.organization.id)
        self.assertFalse(response.data['is_low_stock'])

    def test_employee_can_read_but_cannot_create_stock_record(self):
        employee = self.create_user('stock-employee@example.com')
        OrganizationMembership.objects.create(
            user=employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=self.product,
            quantity='2.00',
            reorder_level='5.00',
        )
        another_product = Product.objects.create(
            organization=self.organization,
            name='Ibuprofen',
            sku='IBU-1',
        )
        self.authenticate(employee)

        list_response = self.client.get('/api/v1/inventory-stocks/')
        create_response = self.client.post(
            '/api/v1/inventory-stocks/',
            {
                'branch': self.branch.id,
                'product': another_product.id,
                'quantity': '10.00',
            },
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertTrue(list_response.data['results'][0]['is_low_stock'])
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stock_requires_branch_and_product_from_same_organization(self):
        other_organization = Organization.objects.create(name='Other Org')
        other_product = Product.objects.create(
            organization=other_organization,
            name='Other Product',
            sku='OTHER-1',
        )
        self.authenticate()

        response = self.client.post(
            '/api/v1/inventory-stocks/',
            {
                'branch': self.branch.id,
                'product': other_product.id,
                'quantity': '10.00',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
