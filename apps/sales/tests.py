from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.inventory.models import InventoryStock, StockMovement
from apps.inventory.services import increase_stock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product, ProductVariant

from .models import Payment, Sale


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
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name='Box',
            sku='SALE-PARA-1-BOX',
            selling_price='120.00',
        )
        increase_stock(
            branch=self.branch,
            product_variant=self.variant,
            quantity='20.00',
            movement_type=StockMovement.MovementType.OPENING_STOCK,
        )
        self.stock = InventoryStock.objects.get(branch=self.branch, product_variant=self.variant)

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def sale_payload(self, quantity='3.00'):
        return {
            'branch': self.branch.id,
            'customer': self.customer.id,
            'reference': 'SO-001',
            'discount_amount': '10.00',
            'tax_amount': '5.00',
            'items': [
                {
                    'product': self.product.id,
                    'product_variant': self.variant.id,
                    'quantity': quantity,
                    'unit_price': '120.00',
                    'discount': '15.00',
                    'tax': '3.00',
                }
            ],
        }

    def create_confirmed_sale(self, quantity='3.00'):
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(quantity=quantity), format='json')
        sale_id = create_response.data['id']
        confirm_response = self.client.post(f'/api/v1/sales/{sale_id}/confirm/')
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        return sale_id

    def test_manager_can_create_sale_draft_with_totals(self):
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
        self.assertRegex(response.data['sale_number'], r'^SL-\d{6}$')
        self.assertEqual(response.data['organization'], self.organization.id)
        self.assertEqual(response.data['subtotal'], '348.00')
        self.assertEqual(response.data['grand_total'], '343.00')
        self.assertEqual(response.data['total_amount'], '343.00')
        self.assertEqual(response.data['payment_status'], Sale.PaymentStatus.UNPAID)
        self.assertEqual(response.data['created_by'], manager.id)

    def test_confirm_action_changes_draft_to_confirmed_and_broadcasts_event(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(), format='json')
        sync_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=sync_group_send):
            response = self.client.post(f'/api/v1/sales/{create_response.data["id"]}/confirm/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Sale.Status.CONFIRMED)
        groups = {call.args[0] for call in sync_group_send.call_args_list}
        self.assertIn(f'organization_{self.organization.id}_sales', groups)
        event = next(call.args[1] for call in sync_group_send.call_args_list if call.args[1]['event'] == 'sale.confirmed')
        self.assertEqual(event['type'], 'realtime.event')

    def test_draft_sale_cannot_be_completed_directly(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(quantity='4.00'), format='json')

        response = self.client.post(f'/api/v1/sales/{create_response.data["id"]}/complete/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.stock.refresh_from_db()
        self.assertEqual(str(self.stock.quantity), '20.00')

    def test_completing_confirmed_sale_decrements_inventory_and_creates_movement(self):
        self.authenticate()
        sale_id = self.create_confirmed_sale(quantity='4.00')

        response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')
        second_response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Sale.Status.COMPLETED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.stock.refresh_from_db()
        self.assertEqual(str(self.stock.quantity), '16.00')
        movement = StockMovement.objects.filter(
            product_variant=self.variant,
            movement_type=StockMovement.MovementType.SALE,
        ).latest('created_at')
        self.assertEqual(str(movement.previous_quantity), '20.00')
        self.assertEqual(str(movement.quantity), '4.00')
        self.assertEqual(str(movement.new_quantity), '16.00')

    def test_completing_sale_broadcasts_sale_and_inventory_events(self):
        self.authenticate()
        sale_id = self.create_confirmed_sale(quantity='4.00')
        inventory_group_send = Mock()
        sale_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=inventory_group_send):
            response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = {call.args[0] for call in inventory_group_send.call_args_list}
        self.assertIn(f'organization_{self.organization.id}_inventory', groups)
        self.assertIn(f'organization_{self.organization.id}_sales', groups)
        sale_event = next(call.args[1] for call in inventory_group_send.call_args_list if call.args[1]['event'] == 'sale.completed')
        self.assertEqual(sale_event['type'], 'realtime.event')

    def test_sale_completion_rejects_insufficient_stock_and_rolls_back(self):
        self.authenticate()
        sale_id = self.create_confirmed_sale(quantity='25.00')

        response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.stock.refresh_from_db()
        self.assertEqual(str(self.stock.quantity), '20.00')
        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(sale.status, Sale.Status.CONFIRMED)
        self.assertFalse(StockMovement.objects.filter(movement_type=StockMovement.MovementType.SALE).exists())

    def test_cancel_action_blocks_later_completion(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/sales/', self.sale_payload(), format='json')
        sale_id = create_response.data['id']

        cancel_response = self.client.post(f'/api/v1/sales/{sale_id}/cancel/')
        complete_response = self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.data['status'], Sale.Status.CANCELLED)
        self.assertEqual(complete_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payments_track_partial_paid_and_reject_overpayment(self):
        self.authenticate()
        sale_id = self.create_confirmed_sale(quantity='1.00')
        self.client.post(f'/api/v1/sales/{sale_id}/complete/')

        partial_response = self.client.post(
            f'/api/v1/sales/{sale_id}/payments/',
            {'amount': '50.00', 'payment_method': Payment.Method.CASH},
            format='json',
        )
        sale_response = self.client.get(f'/api/v1/sales/{sale_id}/')
        full_response = self.client.post(
            f'/api/v1/sales/{sale_id}/payments/',
            {'amount': '53.00', 'payment_method': Payment.Method.MOBILE_BANKING},
            format='json',
        )
        overpayment_response = self.client.post(
            f'/api/v1/sales/{sale_id}/payments/',
            {'amount': '1.00', 'payment_method': Payment.Method.CASH},
            format='json',
        )

        self.assertEqual(partial_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(partial_response.data['payment_status'], Sale.PaymentStatus.PARTIALLY_PAID)
        self.assertEqual(sale_response.data['paid_amount'], '50.00')
        self.assertEqual(sale_response.data['due_amount'], '53.00')
        self.assertEqual(full_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(full_response.data['payment_status'], Sale.PaymentStatus.PAID)
        self.assertEqual(overpayment_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_creation_broadcasts_payment_event(self):
        self.authenticate()
        sale_id = self.create_confirmed_sale(quantity='1.00')
        sync_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=sync_group_send):
            response = self.client.post(
                f'/api/v1/sales/{sale_id}/payments/',
                {'amount': '50.00', 'payment_method': Payment.Method.CASH},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        groups = {call.args[0] for call in sync_group_send.call_args_list}
        self.assertIn(f'organization_{self.organization.id}_payments', groups)
        event = next(call.args[1] for call in sync_group_send.call_args_list if call.args[1]['event'] == 'payment.created')
        self.assertEqual(event['type'], 'realtime.event')

    def test_payment_status_filter_returns_matching_sales(self):
        self.authenticate()
        unpaid_sale_id = self.create_confirmed_sale(quantity='1.00')
        paid_sale_id = self.create_confirmed_sale(quantity='1.00')
        self.client.post(
            f'/api/v1/sales/{paid_sale_id}/payments/',
            {'amount': '103.00', 'payment_method': Payment.Method.CASH},
            format='json',
        )

        unpaid_response = self.client.get('/api/v1/sales/?payment_status=UNPAID')
        paid_response = self.client.get('/api/v1/sales/?payment_status=PAID')

        self.assertEqual({sale['id'] for sale in unpaid_response.data['results']}, {unpaid_sale_id})
        self.assertEqual({sale['id'] for sale in paid_response.data['results']}, {paid_sale_id})

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

    def test_sale_rejects_product_from_other_organization(self):
        other_organization = Organization.objects.create(name='Other Sale Org')
        other_product = Product.objects.create(
            organization=other_organization,
            name='Other Product',
            sku='OTHER-SALE-1',
        )
        payload = self.sale_payload()
        payload['items'][0].pop('product_variant')
        payload['items'][0]['product'] = other_product.id
        self.authenticate()

        response = self.client.post('/api/v1/sales/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
