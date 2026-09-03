from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.expenses.models import Expense, ExpenseCategory
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.sales.models import Payment, Sale, SaleItem

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
