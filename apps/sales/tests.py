from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.inventory.models import InventoryStock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product

from .models import Sale


class SaleAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='sale-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Sale Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.customer = Customer.objects.create(organization=self.organization, name='Walk-in Customer')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Paracetamol',
            sku='SALE-PARA-1',
            selling_price='120.00',
        )
        self.stock = InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=self.product,
            quantity='20.00',
            reorder_level='5.00',
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def sale_payload(self, quantity='3.00'):
        return {
            'branch': self.branch.id,
            'customer': self.customer.id,
            'reference': 'SO-001',
            'items': [
                {
                    'product': self.product.id,
                    'quantity': quantity,
                    'unit_price': '120.00',
                }
            ],
        }

    def test_manager_can_create_sale_draft(self):
        manager = self.create_user('sale-manager@example.com')
        OrganizationMembership.objects.create(
            user=manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.authenticate(manager)

        response = self.client.post('/api/v1/sales/', self.sale_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Sale.Status.DRAFT)
        self.assertEqual(response.data['organization'], self.organization.id)
        self.assertEqual(response.data['total_amount'], '360.00')

    def test_completing_sale_decrements_inventory_and_broadcasts_stock_update(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(quantity='4.00'), format='json')
        sale_id = create_response.data['id']
        sync_group_send = Mock()

        with patch('apps.inventory.events.async_to_sync', return_value=sync_group_send):
            response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock.refresh_from_db()
        self.assertEqual(str(self.stock.quantity), '16.00')
        self.assertEqual(sync_group_send.call_count, 2)
        groups = {call.args[0] for call in sync_group_send.call_args_list}
        self.assertEqual(
            groups,
            {f'organization_{self.organization.id}', f'organization_{self.organization.id}_inventory'},
        )
        event = sync_group_send.call_args_list[0].args[1]
        self.assertEqual(event['type'], 'inventory.stock_updated')
        self.assertEqual(event['data']['quantity'], '16.00')

    def test_completing_sale_twice_does_not_decrement_stock_twice(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(quantity='4.00'), format='json')
        sale_id = create_response.data['id']

        first_response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')
        second_response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.stock.refresh_from_db()
        self.assertEqual(str(self.stock.quantity), '16.00')

    def test_sale_completion_rejects_insufficient_stock(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(quantity='25.00'), format='json')
        sale_id = create_response.data['id']

        response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.stock.refresh_from_db()
        self.assertEqual(str(self.stock.quantity), '20.00')

    def test_employee_can_read_but_cannot_create_sale(self):
        employee = self.create_user('sale-employee@example.com')
        OrganizationMembership.objects.create(
            user=employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        Sale.objects.create(
            organization=self.organization,
            branch=self.branch,
            customer=self.customer,
            reference='SO-READ',
        )
        self.authenticate(employee)

        list_response = self.client.get('/api/v1/sales/')
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(), format='json')

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
