from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.inventory.models import InventoryStock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Sale, SaleItem
from apps.suppliers.models import Supplier


class QueryProfileTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='query-profiler@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Query Profile Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.customer = Customer.objects.create(organization=self.organization, name='Query Customer')
        self.supplier = Supplier.objects.create(organization=self.organization, name='Query Supplier')

        self.products = [
            Product.objects.create(
                organization=self.organization,
                name=f'Profile Product {index}',
                sku=f'PROFILE-{index}',
                cost_price='50.00',
                selling_price='100.00',
            )
            for index in range(25)
        ]
        for product in self.products:
            InventoryStock.objects.create(
                organization=self.organization,
                branch=self.branch,
                product=product,
                quantity='10.00',
                reorder_level='2.00',
            )

        for index, product in enumerate(self.products[:10]):
            sale = Sale.objects.create(
                organization=self.organization,
                branch=self.branch,
                customer=self.customer,
                status=Sale.Status.COMPLETED,
                sale_date=date(2026, 9, 3),
                created_by=self.user,
            )
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity='1.00',
                unit_price='100.00',
                unit_cost='50.00',
            )
            sale.recalculate_totals()

            purchase = Purchase.objects.create(
                organization=self.organization,
                branch=self.branch,
                supplier=self.supplier,
                status=Purchase.Status.RECEIVED,
                created_by=self.user,
            )
            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity='2.00',
                unit_cost='50.00',
            )
            purchase.recalculate_totals()

        self.client.force_authenticate(self.user)

    def assert_profiled_endpoint(self, path, max_queries):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(path)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(
            len(queries),
            max_queries,
            f'{path} executed {len(queries)} queries, expected <= {max_queries}',
        )

    def test_product_list_query_profile(self):
        self.assert_profiled_endpoint('/api/v1/products/', max_queries=12)

    def test_inventory_list_query_profile(self):
        self.assert_profiled_endpoint('/api/v1/inventory/', max_queries=14)

    def test_sales_list_query_profile(self):
        self.assert_profiled_endpoint('/api/v1/sales/', max_queries=16)

    def test_purchase_list_query_profile(self):
        self.assert_profiled_endpoint('/api/v1/purchases/', max_queries=14)

    def test_dashboard_query_profile(self):
        self.assert_profiled_endpoint(
            f'/api/v1/dashboard/summary/?organization={self.organization.id}',
            max_queries=18,
        )
