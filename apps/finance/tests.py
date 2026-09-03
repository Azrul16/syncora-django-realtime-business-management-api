from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import InventoryStock
from apps.notifications.event_types import EventType
from apps.notifications.services.event_dispatcher import dispatch_event
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Payment, Sale, SaleItem
from apps.suppliers.models import Supplier

from .services.financial_summary import FinancialSummaryService


class FinancialSummaryTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='finance-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Finance Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.other_branch = Branch.objects.create(organization=self.organization, name='Khulna')
        self.customer = Customer.objects.create(organization=self.organization, name='Finance Customer')
        self.category = ExpenseCategory.objects.create(organization=self.organization, name='Rent')
        self.supplier = Supplier.objects.create(organization=self.organization, name='Analytics Supplier')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Finance Product',
            sku='FIN-PROD-1',
            cost_price='100.00',
            selling_price='150.00',
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_sale(self, *, branch=None, quantity='2.00', unit_price='150.00', unit_cost='100.00'):
        sale = Sale.objects.create(
            organization=self.organization,
            branch=branch or self.branch,
            customer=self.customer,
            status=Sale.Status.COMPLETED,
            sale_date=date(2026, 9, 2),
            created_by=self.user,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
        )
        sale.recalculate_totals()
        return sale

    def create_expense(self, *, status_value=Expense.Status.APPROVED, branch=None, amount='70000.00'):
        return Expense.objects.create(
            organization=self.organization,
            branch=branch or self.branch,
            category=self.category,
            title='Finance Expense',
            amount=amount,
            expense_date=date(2026, 9, 2),
            status=status_value,
            created_by=self.user,
        )

    def test_draft_expense_does_not_affect_financial_summary_until_approved(self):
        expense = self.create_expense(status_value=Expense.Status.DRAFT, amount='10000.00')
        service = FinancialSummaryService(self.organization)

        self.assertEqual(service.get_expense_summary()['total'], 0)

        expense.approve(self.user)

        self.assertEqual(service.get_expense_summary()['total'], 10000)

    def test_gross_profit_uses_sale_item_cost_snapshot(self):
        self.create_sale(quantity='2.00', unit_price='150.00', unit_cost='100.00')
        service = FinancialSummaryService(self.organization)

        summary = service.get_profit_summary()

        self.assertEqual(summary['revenue'], 300)
        self.assertEqual(summary['cost_of_goods_sold'], 200)
        self.assertEqual(summary['gross_profit'], 100)

    def test_partial_payment_keeps_revenue_separate_from_cash_received(self):
        sale = self.create_sale(quantity='1.00', unit_price='100000.00', unit_cost='70000.00')
        Payment.objects.create(
            sale=sale,
            amount='60000.00',
            payment_method=Payment.Method.CASH,
            received_by=self.user,
        )
        service = FinancialSummaryService(self.organization)

        self.assertEqual(service.get_sales_summary()['revenue'], 100000)
        self.assertEqual(service.get_payment_summary()['received'], 60000)
        self.assertEqual(service.get_payment_summary()['outstanding'], 40000)

    def test_net_cash_flow_uses_payments_minus_approved_expenses(self):
        sale = self.create_sale(quantity='1.00', unit_price='200000.00', unit_cost='120000.00')
        Payment.objects.create(sale=sale, amount='200000.00', received_by=self.user)
        self.create_expense(amount='70000.00')
        service = FinancialSummaryService(self.organization)

        summary = service.get_cash_flow_summary()

        self.assertEqual(summary['cash_in'], 200000)
        self.assertEqual(summary['cash_out'], 70000)
        self.assertEqual(summary['net_cash_flow'], 130000)

    def test_finance_endpoint_is_tenant_scoped(self):
        other_user = get_user_model().objects.create_user(
            email='finance-other@example.com',
            password='test-pass-1234',
        )
        other_organization = Organization.objects.create(name='Other Finance Org')
        other_branch = Branch.objects.create(organization=other_organization, name='Other Branch')
        other_customer = Customer.objects.create(organization=other_organization, name='Other Customer')
        other_product = Product.objects.create(
            organization=other_organization,
            name='Other Product',
            sku='OTHER-FIN-1',
        )
        OrganizationMembership.objects.create(
            user=other_user,
            organization=other_organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.create_sale(quantity='1.00', unit_price='500000.00', unit_cost='300000.00')
        other_sale = Sale.objects.create(
            organization=other_organization,
            branch=other_branch,
            customer=other_customer,
            status=Sale.Status.COMPLETED,
        )
        SaleItem.objects.create(
            sale=other_sale,
            product=other_product,
            quantity='1.00',
            unit_price='200000.00',
        )
        other_sale.recalculate_totals()
        self.authenticate()

        response = self.client.get(f'/api/v1/finance/summary/?organization={self.organization.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sales']['revenue'], '500000.00')

    def test_finance_endpoint_filters_by_branch_and_date_range(self):
        dhaka_sale = self.create_sale(
            branch=self.branch,
            quantity='1.00',
            unit_price='300000.00',
            unit_cost='200000.00',
        )
        khulna_sale = self.create_sale(
            branch=self.other_branch,
            quantity='1.00',
            unit_price='200000.00',
            unit_cost='100000.00',
        )
        self.create_expense(branch=self.branch, amount='50000.00')
        self.create_expense(branch=self.other_branch, amount='25000.00')
        Payment.objects.create(sale=dhaka_sale, amount='300000.00', received_by=self.user)
        Payment.objects.create(sale=khulna_sale, amount='200000.00', received_by=self.user)
        self.authenticate()

        response = self.client.get(
            f'/api/v1/finance/summary/?organization={self.organization.id}'
            f'&branch={self.branch.id}&date_from=2026-09-01&date_to=2026-09-30'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sales']['revenue'], '300000.00')
        self.assertEqual(response.data['payments']['received'], '300000.00')
        self.assertEqual(response.data['expenses']['total'], '50000.00')
        self.assertEqual(response.data['cash_flow']['net_cash_flow'], '250000.00')

    def test_approving_expense_broadcasts_finance_update(self):
        expense = self.create_expense(status_value=Expense.Status.DRAFT, amount='10000.00')
        self.authenticate()
        sync_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=sync_group_send):
            response = self.client.post(f'/api/v1/expenses/{expense.id}/approve/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = {call.args[0] for call in sync_group_send.call_args_list}
        self.assertIn(f'organization_{self.organization.id}_finance', groups)
        event = next(call.args[1] for call in sync_group_send.call_args_list if call.args[1]['event'] == 'expense.approved')
        self.assertEqual(event['type'], 'realtime.event')

    def test_dashboard_summary_returns_core_kpis(self):
        sale = self.create_sale(quantity='1.00', unit_price='1000.00', unit_cost='600.00')
        Payment.objects.create(sale=sale, amount='800.00', received_by=self.user)
        self.create_expense(amount='100.00')
        InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=self.product,
            quantity='3.00',
            reorder_level='5.00',
        )
        self.authenticate()

        response = self.client.get(f'/api/v1/dashboard/summary/?organization={self.organization.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['today']['revenue'], '1000.00')
        self.assertEqual(response.data['today']['sales_count'], 1)
        self.assertEqual(response.data['today']['gross_profit'], '400.00')
        self.assertEqual(response.data['today']['cash_received'], '800.00')
        self.assertEqual(response.data['inventory']['low_stock'], 1)

    def test_sales_and_profit_trends_group_by_date(self):
        self.create_sale(quantity='1.00', unit_price='1000.00', unit_cost='600.00')
        self.create_sale(quantity='1.00', unit_price='2000.00', unit_cost='1400.00')
        self.authenticate()

        sales_response = self.client.get(
            f'/api/v1/dashboard/sales-trend/?organization={self.organization.id}'
            '&date_from=2026-09-01&date_to=2026-09-30'
        )
        profit_response = self.client.get(
            f'/api/v1/dashboard/profit-trend/?organization={self.organization.id}'
            '&date_from=2026-09-01&date_to=2026-09-30'
        )

        self.assertEqual(sales_response.status_code, status.HTTP_200_OK)
        self.assertEqual(sales_response.data[0]['revenue'], '3000.00')
        self.assertEqual(sales_response.data[0]['sales_count'], 2)
        self.assertEqual(profit_response.data[0]['revenue'], '3000.00')
        self.assertEqual(profit_response.data[0]['cogs'], '2000.00')
        self.assertEqual(profit_response.data[0]['gross_profit'], '1000.00')

    def test_dashboard_branch_filter_does_not_mix_branch_revenue(self):
        self.create_sale(branch=self.branch, quantity='1.00', unit_price='5000.00', unit_cost='3000.00')
        self.create_sale(branch=self.other_branch, quantity='1.00', unit_price='3000.00', unit_cost='2000.00')
        self.authenticate()

        response = self.client.get(
            f'/api/v1/dashboard/summary/?organization={self.organization.id}&branch={self.branch.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['today']['revenue'], '5000.00')

    def test_top_products_orders_by_quantity_sold(self):
        second_product = Product.objects.create(
            organization=self.organization,
            name='Second Product',
            sku='FIN-PROD-2',
            cost_price='50.00',
            selling_price='80.00',
        )
        sale = self.create_sale(quantity='20.00', unit_price='100.00', unit_cost='60.00')
        SaleItem.objects.create(
            sale=sale,
            product=second_product,
            quantity='10.00',
            unit_price='80.00',
            unit_cost='50.00',
        )
        sale.recalculate_totals()
        self.authenticate()

        response = self.client.get(f'/api/v1/dashboard/top-products/?organization={self.organization.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['product'], 'Finance Product')
        self.assertEqual(response.data[0]['quantity_sold'], '20.00')

    def test_inventory_summary_calculates_stock_value_and_stock_risk(self):
        second_product = Product.objects.create(
            organization=self.organization,
            name='Out Product',
            sku='FIN-PROD-OUT',
            cost_price='100.00',
            selling_price='150.00',
        )
        InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=self.product,
            quantity='10.00',
            reorder_level='5.00',
        )
        InventoryStock.objects.create(
            organization=self.organization,
            branch=self.branch,
            product=second_product,
            quantity='0.00',
            reorder_level='5.00',
        )
        self.authenticate()

        response = self.client.get(f'/api/v1/dashboard/inventory-summary/?organization={self.organization.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_units'], '10.00')
        self.assertEqual(response.data['inventory_cost_value'], '1000.00')
        self.assertEqual(response.data['potential_sale_value'], '1500.00')
        self.assertEqual(response.data['low_stock_products'], 1)
        self.assertEqual(response.data['out_of_stock_products'], 1)

    def test_dashboard_tenant_isolation(self):
        other_organization = Organization.objects.create(name='Other Dashboard Org')
        other_user = get_user_model().objects.create_user(
            email='dashboard-other@example.com',
            password='test-pass-1234',
        )
        other_branch = Branch.objects.create(organization=other_organization, name='Other Branch')
        other_customer = Customer.objects.create(organization=other_organization, name='Other Customer')
        other_product = Product.objects.create(
            organization=other_organization,
            name='Other Dashboard Product',
            sku='OTHER-DASH-1',
        )
        OrganizationMembership.objects.create(
            user=other_user,
            organization=other_organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.create_sale(quantity='1.00', unit_price='1000000.00', unit_cost='700000.00')
        other_sale = Sale.objects.create(
            organization=other_organization,
            branch=other_branch,
            customer=other_customer,
            status=Sale.Status.COMPLETED,
        )
        SaleItem.objects.create(
            sale=other_sale,
            product=other_product,
            quantity='1.00',
            unit_price='500000.00',
            unit_cost='300000.00',
        )
        other_sale.recalculate_totals()
        self.authenticate()

        response = self.client.get(f'/api/v1/dashboard/summary/?organization={self.organization.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['today']['revenue'], '1000000.00')

    def test_customer_and_supplier_analytics_endpoints(self):
        sale = self.create_sale(quantity='1.00', unit_price='850000.00', unit_cost='500000.00')
        Payment.objects.create(sale=sale, amount='800000.00', received_by=self.user)
        purchase = Purchase.objects.create(
            organization=self.organization,
            branch=self.branch,
            supplier=self.supplier,
            status=Purchase.Status.RECEIVED,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity='2.00',
            unit_cost='100000.00',
        )
        purchase.recalculate_totals()
        self.authenticate()

        customers_response = self.client.get(f'/api/v1/dashboard/customers/?organization={self.organization.id}')
        customer_summary_response = self.client.get(f'/api/v1/customers/{self.customer.id}/summary/')
        suppliers_response = self.client.get(f'/api/v1/dashboard/suppliers/?organization={self.organization.id}')
        supplier_summary_response = self.client.get(f'/api/v1/suppliers/{self.supplier.id}/summary/')

        self.assertEqual(customers_response.status_code, status.HTTP_200_OK)
        self.assertEqual(customers_response.data['top_customers'][0]['total_spent'], '850000.00')
        self.assertEqual(customer_summary_response.data['outstanding_due'], '50000.00')
        self.assertEqual(suppliers_response.data['top_suppliers'][0]['total_purchase_value'], '200000.00')
        self.assertEqual(supplier_summary_response.data['purchase_orders'], 1)

    def test_business_event_broadcasts_dashboard_update(self):
        sync_group_send = Mock()

        with patch('apps.notifications.services.event_dispatcher.async_to_sync', return_value=sync_group_send):
            dispatch_event(
                event=EventType.SALE_COMPLETED,
                organization=self.organization,
                actor=self.user,
                branch=self.branch,
                data={'sale_number': 'SL-000212', 'total': '50000.00'},
                groups=[f'organization_{self.organization.id}_sales'],
            )

        dashboard_event = next(
            call.args[1]
            for call in sync_group_send.call_args_list
            if call.args[0] == f'organization_{self.organization.id}_dashboard'
        )
        self.assertEqual(dashboard_event['event'], EventType.DASHBOARD_UPDATED)
        self.assertEqual(dashboard_event['data']['reason'], EventType.SALE_COMPLETED)
