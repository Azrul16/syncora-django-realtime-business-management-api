from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.inventory.models import InventoryStock, StockMovement
from apps.inventory.services import increase_stock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product, ProductVariant
from apps.suppliers.models import Supplier

from .models import Purchase, PurchaseItem


class PurchaseAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='purchase-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Purchase Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.supplier = Supplier.objects.create(organization=self.organization, name='Acme Supply')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Paracetamol',
            sku='PUR-PARA-1',
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name='Box',
            sku='PUR-PARA-1-BOX',
            cost_price='80.00',
            selling_price='120.00',
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def purchase_payload(self):
        return {
            'branch': self.branch.id,
            'supplier': self.supplier.id,
            'reference': 'PO-001',
            'discount_amount': '50.00',
            'tax_amount': '25.00',
            'shipping_cost': '10.00',
            'items': [
                {
                    'product': self.product.id,
                    'product_variant': self.variant.id,
                    'quantity': '10.00',
                    'unit_cost': '80.00',
                    'discount': '20.00',
                    'tax': '5.00',
                }
            ],
        }

    def test_manager_can_create_purchase_draft(self):
        manager = self.create_user('purchase-manager@example.com')
        OrganizationMembership.objects.create(
            user=manager,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.authenticate(manager)

        response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Purchase.Status.DRAFT)
        self.assertRegex(response.data['purchase_number'], r'^PO-\d{6}$')
        self.assertEqual(response.data['organization'], self.organization.id)
        self.assertEqual(response.data['subtotal'], '785.00')
        self.assertEqual(response.data['grand_total'], '770.00')
        self.assertEqual(response.data['total_amount'], '770.00')
        self.assertFalse(InventoryStock.objects.exists())

    def test_purchase_order_action_changes_draft_to_ordered(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')
        purchase_id = create_response.data['id']

        response = self.client.post(f'/api/v1/purchases/{purchase_id}/order/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Purchase.Status.ORDERED)

    def test_receiving_ordered_purchase_increases_inventory_stock_and_creates_movement(self):
        self.authenticate()
        increase_stock(
            branch=self.branch,
            product_variant=self.variant,
            quantity='10.00',
            movement_type=StockMovement.MovementType.OPENING_STOCK,
        )
        create_response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')
        purchase_id = create_response.data['id']
        order_response = self.client.post(f'/api/v1/purchases/{purchase_id}/order/')

        receive_response = self.client.post(f'/api/v1/purchases/{purchase_id}/receive/')
        second_receive_response = self.client.post(f'/api/v1/purchases/{purchase_id}/receive/')

        self.assertEqual(order_response.status_code, status.HTTP_200_OK)
        self.assertEqual(receive_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_receive_response.status_code, status.HTTP_400_BAD_REQUEST)

        stock = InventoryStock.objects.get(branch=self.branch, product_variant=self.variant)
        self.assertEqual(str(stock.quantity), '20.00')
        movement = StockMovement.objects.filter(
            product_variant=self.variant,
            movement_type=StockMovement.MovementType.PURCHASE,
        ).latest('created_at')
        self.assertEqual(str(movement.previous_quantity), '10.00')
        self.assertEqual(str(movement.quantity), '10.00')
        self.assertEqual(str(movement.new_quantity), '20.00')

    def test_receiving_purchase_broadcasts_purchase_event(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')
        purchase_id = create_response.data['id']
        self.client.post(f'/api/v1/purchases/{purchase_id}/order/')
        sync_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=sync_group_send):
            response = self.client.post(f'/api/v1/purchases/{purchase_id}/receive/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = {call.args[0] for call in sync_group_send.call_args_list}
        self.assertIn(f'organization_{self.organization.id}_purchases', groups)
        event = next(call.args[1] for call in sync_group_send.call_args_list if call.args[1]['event'] == 'purchase.received')
        self.assertEqual(event['type'], 'realtime.event')
        self.assertEqual(event['data']['status'], Purchase.Status.RECEIVED)

    def test_draft_purchase_cannot_be_received_directly(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')

        response = self.client.post(f'/api/v1/purchases/{create_response.data["id"]}/receive/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(InventoryStock.objects.exists())

    def test_employee_can_read_but_cannot_create_purchase(self):
        employee = self.create_user('purchase-employee@example.com')
        OrganizationMembership.objects.create(
            user=employee,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        Purchase.objects.create(
            organization=self.organization,
            branch=self.branch,
            supplier=self.supplier,
            reference='PO-READ',
            purchase_number='PO-999991',
        )
        self.authenticate(employee)

        list_response = self.client.get('/api/v1/purchases/')
        create_response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_purchase_rejects_product_from_other_organization(self):
        other_organization = Organization.objects.create(name='Other Purchase Org')
        other_product = Product.objects.create(
            organization=other_organization,
            name='Other Product',
            sku='OTHER-PUR-1',
        )
        payload = self.purchase_payload()
        payload['items'][0]['product'] = other_product.id
        self.authenticate()

        response = self.client.post('/api/v1/purchases/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_supplier_is_hidden_from_non_members(self):
        outsider = self.create_user('purchase-outsider@example.com')
        self.authenticate(outsider)

        response = self.client.get(f'/api/v1/suppliers/{self.supplier.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_action_blocks_later_receiving(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')
        purchase_id = create_response.data['id']

        cancel_response = self.client.post(f'/api/v1/purchases/{purchase_id}/cancel/')
        receive_response = self.client.post(f'/api/v1/purchases/{purchase_id}/receive/')

        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.data['status'], Purchase.Status.CANCELLED)
        self.assertEqual(receive_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receiving_rolls_back_if_any_item_fails(self):
        self.authenticate()
        second_product = Product.objects.create(
            organization=self.organization,
            name='Ibuprofen',
            sku='PUR-IBU-1',
        )
        second_variant = ProductVariant.objects.create(
            product=second_product,
            name='Box',
            sku='PUR-IBU-1-BOX',
        )
        purchase = Purchase.objects.create(
            organization=self.organization,
            branch=self.branch,
            supplier=self.supplier,
            reference='PO-ROLLBACK',
            status=Purchase.Status.ORDERED,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            product_variant=self.variant,
            quantity='5.00',
            unit_cost='80.00',
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=second_product,
            product_variant=second_variant,
            quantity='5.00',
            unit_cost='100.00',
        )

        def fail_for_second_item(*args, **kwargs):
            if kwargs.get('product_variant') == second_variant:
                raise ValueError('forced failure')
            return increase_stock(*args, **kwargs)

        with patch('apps.inventory.services.increase_stock', side_effect=fail_for_second_item):
            with self.assertRaises(ValueError):
                purchase.receive()

        self.assertFalse(InventoryStock.objects.filter(product_variant=self.variant).exists())
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, Purchase.Status.ORDERED)
