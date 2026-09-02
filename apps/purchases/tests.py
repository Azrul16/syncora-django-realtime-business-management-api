from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.inventory.models import InventoryStock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.suppliers.models import Supplier

from .models import Purchase


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

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_user(self, email):
        return get_user_model().objects.create_user(email=email, password='test-pass-1234')

    def purchase_payload(self):
        return {
            'branch': self.branch.id,
            'supplier': self.supplier.id,
            'reference': 'PO-001',
            'items': [
                {
                    'product': self.product.id,
                    'quantity': '10.00',
                    'unit_cost': '80.00',
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
        self.assertEqual(response.data['organization'], self.organization.id)
        self.assertEqual(response.data['total_amount'], '800.00')
        self.assertFalse(InventoryStock.objects.exists())

    def test_receiving_purchase_increases_inventory_stock(self):
        self.authenticate()
        create_response = self.client.post('/api/v1/purchases/', self.purchase_payload(), format='json')
        purchase_id = create_response.data['id']

        receive_response = self.client.post(f'/api/v1/purchases/{purchase_id}/receive/')
        second_receive_response = self.client.post(f'/api/v1/purchases/{purchase_id}/receive/')

        self.assertEqual(receive_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_receive_response.status_code, status.HTTP_200_OK)

        stock = InventoryStock.objects.get(branch=self.branch, product=self.product)
        self.assertEqual(str(stock.quantity), '10.00')

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
