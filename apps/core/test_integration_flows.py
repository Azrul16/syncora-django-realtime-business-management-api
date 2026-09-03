from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.inventory.models import InventoryStock, StockMovement
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.purchases.models import Purchase
from apps.sales.models import Sale
from apps.suppliers.models import Supplier


class BackendIntegrationFlowTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='integration-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Integration Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Integration Product',
            sku='INT-PROD-1',
            cost_price='40.00',
            selling_price='100.00',
        )
        self.client.force_authenticate(self.user)

    def test_full_purchasing_flow_receives_inventory_and_activity(self):
        supplier_response = self.client.post(
            '/api/v1/suppliers/',
            {'organization': self.organization.id, 'name': 'Integration Supplier'},
            format='json',
        )
        purchase_response = self.client.post(
            '/api/v1/purchases/',
            {
                'branch': self.branch.id,
                'supplier': supplier_response.data['id'],
                'items': [
                    {
                        'product': self.product.id,
                        'quantity': '5.00',
                        'unit_cost': '40.00',
                    }
                ],
            },
            format='json',
        )
        order_response = self.client.post(f'/api/v1/purchases/{purchase_response.data["id"]}/order/')
        receive_response = self.client.post(f'/api/v1/purchases/{purchase_response.data["id"]}/receive/')

        self.assertEqual(supplier_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(purchase_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(order_response.status_code, status.HTTP_200_OK)
        self.assertEqual(receive_response.status_code, status.HTTP_200_OK)
        self.assertEqual(receive_response.data['status'], Purchase.Status.RECEIVED)
        stock = InventoryStock.objects.get(branch=self.branch, product=self.product)
        self.assertEqual(str(stock.quantity), '5.00')
        self.assertTrue(
            StockMovement.objects.filter(
                product=self.product,
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity='5.00',
            ).exists()
        )

    def test_full_sales_flow_updates_inventory_payments_and_finance(self):
        customer_response = self.client.post(
            '/api/v1/customers/',
            {'organization': self.organization.id, 'name': 'Integration Customer'},
            format='json',
        )
        InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=self.product,
            quantity='3.00',
            reorder_level='1.00',
        )
        sale_response = self.client.post(
            '/api/v1/sales/',
            {
                'branch': self.branch.id,
                'customer': customer_response.data['id'],
                'items': [
                    {
                        'product': self.product.id,
                        'quantity': '2.00',
                        'unit_price': '100.00',
                    }
                ],
            },
            format='json',
        )
        confirm_response = self.client.post(f'/api/v1/sales/{sale_response.data["id"]}/confirm/')
        complete_response = self.client.post(f'/api/v1/sales/{sale_response.data["id"]}/complete/')
        payment_response = self.client.post(
            f'/api/v1/sales/{sale_response.data["id"]}/payments/',
            {'amount': '200.00', 'payment_method': 'CASH'},
            format='json',
        )
        finance_response = self.client.get(f'/api/v1/finance/summary/?organization={self.organization.id}')

        self.assertEqual(customer_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(sale_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(finance_response.data['sales']['revenue'], '200.00')
        self.assertEqual(finance_response.data['payments']['received'], '200.00')
        stock = InventoryStock.objects.get(branch=self.branch, product=self.product)
        self.assertEqual(str(stock.quantity), '1.00')

    def test_complete_business_data_stays_tenant_isolated(self):
        other_user = get_user_model().objects.create_user(
            email='integration-other@example.com',
            password='test-pass-1234',
        )
        other_org = Organization.objects.create(name='Other Integration Org')
        other_branch = Branch.objects.create(organization=other_org, name='Other Branch')
        other_customer = Customer.objects.create(organization=other_org, name='Other Customer')
        other_product = Product.objects.create(organization=other_org, name='Other Product', sku='OTHER-INT-1')
        OrganizationMembership.objects.create(
            user=other_user,
            organization=other_org,
            role=OrganizationMembership.Role.OWNER,
        )
        Sale.objects.create(
            organization=other_org,
            branch=other_branch,
            customer=other_customer,
            status=Sale.Status.COMPLETED,
        )
        self.client.force_authenticate(other_user)
        hidden_response = self.client.get('/api/v1/products/')
        self.client.force_authenticate(self.user)
        cross_tenant_response = self.client.get(f'/api/v1/products/{other_product.id}/')

        self.assertEqual(hidden_response.data['count'], 1)
        self.assertEqual(cross_tenant_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_realtime_activity_is_emitted_when_sale_completes(self):
        customer = Customer.objects.create(organization=self.organization, name='Realtime Customer')
        InventoryStock.objects.create(organization=self.organization, branch=self.branch, product=self.product, quantity='2.00')
        sale_response = self.client.post(
            '/api/v1/sales/',
            {
                'branch': self.branch.id,
                'customer': customer.id,
                'items': [{'product': self.product.id, 'quantity': '1.00', 'unit_price': '100.00'}],
            },
            format='json',
        )
        self.client.post(f'/api/v1/sales/{sale_response.data["id"]}/confirm/')
        sync_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=sync_group_send):
            response = self.client.post(f'/api/v1/sales/{sale_response.data["id"]}/complete/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = {call.args[0] for call in sync_group_send.call_args_list}
        self.assertIn(f'organization_{self.organization.id}_sales', groups)
        self.assertIn(f'organization_{self.organization.id}_dashboard', groups)

    def test_sale_completion_rolls_back_inventory_when_stock_decrease_fails(self):
        customer = Customer.objects.create(organization=self.organization, name='Rollback Customer')
        stock = InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=self.product,
            quantity='2.00',
        )
        sale_response = self.client.post(
            '/api/v1/sales/',
            {
                'branch': self.branch.id,
                'customer': customer.id,
                'items': [{'product': self.product.id, 'quantity': '1.00', 'unit_price': '100.00'}],
            },
            format='json',
        )
        self.client.post(f'/api/v1/sales/{sale_response.data["id"]}/confirm/')

        with patch('apps.inventory.services.decrease_stock', side_effect=ValidationError('Injected failure.')):
            response = self.client.post(f'/api/v1/sales/{sale_response.data["id"]}/complete/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        stock.refresh_from_db()
        sale = Sale.objects.get(id=sale_response.data['id'])
        self.assertEqual(str(stock.quantity), '2.00')
        self.assertEqual(sale.status, Sale.Status.CONFIRMED)
        self.assertFalse(
            StockMovement.objects.filter(
                product=self.product,
                movement_type=StockMovement.MovementType.SALE,
            ).exists()
        )
