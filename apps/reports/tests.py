from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.inventory.models import InventoryStock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Sale, SaleItem
from apps.suppliers.models import Supplier


class OrganizationDashboardTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='report-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Report Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Paracetamol',
            sku='REPORT-PARA-1',
        )
        self.customer = Customer.objects.create(organization=self.organization, name='Report Customer')
        self.supplier = Supplier.objects.create(organization=self.organization, name='Report Supplier')

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def test_dashboard_returns_organization_summary(self):
        InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=self.product,
            quantity='4.00',
            reorder_level='5.00',
        )
        purchase = Purchase.objects.create(
            organization=self.organization,
            branch=self.branch,
            supplier=self.supplier,
            status=Purchase.Status.RECEIVED,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity='10.00',
            unit_cost='80.00',
        )
        sale = Sale.objects.create(
            organization=self.organization,
            branch=self.branch,
            customer=self.customer,
            status=Sale.Status.COMPLETED,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity='3.00',
            unit_price='120.00',
        )
        sale.recalculate_totals()
        Expense.objects.create(
            organization=self.organization,
            branch=self.branch,
            title='Rent',
            amount='100.00',
            expense_date=date.today(),
            status=Expense.Status.APPROVED,
        )
        self.authenticate()

        response = self.client.get(f'/api/v1/organizations/{self.organization.id}/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['branches'], 1)
        self.assertEqual(response.data['products'], 1)
        self.assertEqual(response.data['customers'], 1)
        self.assertEqual(response.data['suppliers'], 1)
        self.assertEqual(response.data['inventory_units'], '4.00')
        self.assertEqual(response.data['low_stock_items'], 1)
        self.assertEqual(response.data['purchase_total'], '800.00')
        self.assertEqual(response.data['sales_total'], '360.00')
        self.assertEqual(response.data['expenses_total'], '100.00')

    def test_dashboard_is_hidden_from_non_members(self):
        outsider = get_user_model().objects.create_user(
            email='report-outsider@example.com',
            password='test-pass-1234',
        )
        self.authenticate(outsider)

        response = self.client.get(f'/api/v1/organizations/{self.organization.id}/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
