from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import InventoryStock
from apps.inventory.services import increase_stock
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import Product
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Payment, Sale, SaleItem
from apps.suppliers.models import Supplier


class ConcurrencyProtectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='concurrency-owner@example.com',
            password='test-pass-1234',
        )
        self.organization = Organization.objects.create(name='Concurrency Org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.branch = Branch.objects.create(organization=self.organization, name='Dhaka')
        self.customer = Customer.objects.create(organization=self.organization, name='Concurrent Customer')
        self.supplier = Supplier.objects.create(organization=self.organization, name='Concurrent Supplier')
        self.category = ExpenseCategory.objects.create(organization=self.organization, name='Concurrent Expense')
        self.product = Product.objects.create(
            organization=self.organization,
            name='Concurrent Product',
            sku='CONCURRENT-1',
            cost_price='10.00',
            selling_price='20.00',
        )

    def test_second_stale_sale_completion_is_rejected(self):
        increase_stock(branch=self.branch, product=self.product, quantity='1.00')
        sale = Sale.objects.create(
            organization=self.organization,
            branch=self.branch,
            customer=self.customer,
            status=Sale.Status.CONFIRMED,
            sale_date=date(2026, 9, 3),
            created_by=self.user,
        )
        SaleItem.objects.create(sale=sale, product=self.product, quantity='1.00', unit_price='20.00', unit_cost='10.00')
        sale.recalculate_totals()
        stale_sale = Sale.objects.get(pk=sale.pk)

        sale.complete()

        with self.assertRaises(ValidationError):
            stale_sale.complete()
        stock = InventoryStock.objects.get(branch=self.branch, product=self.product)
        self.assertEqual(str(stock.quantity), '0.00')

    def test_second_stale_purchase_receive_is_rejected(self):
        purchase = Purchase.objects.create(
            organization=self.organization,
            branch=self.branch,
            supplier=self.supplier,
            status=Purchase.Status.ORDERED,
            created_by=self.user,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity='2.00',
            unit_cost='10.00',
        )
        purchase.recalculate_totals()
        stale_purchase = Purchase.objects.get(pk=purchase.pk)

        purchase.receive()

        with self.assertRaises(ValidationError):
            stale_purchase.receive()
        stock = InventoryStock.objects.get(branch=self.branch, product=self.product)
        self.assertEqual(str(stock.quantity), '2.00')

    def test_stale_payment_cannot_exceed_locked_sale_balance(self):
        sale = Sale.objects.create(
            organization=self.organization,
            branch=self.branch,
            customer=self.customer,
            status=Sale.Status.COMPLETED,
            sale_date=date(2026, 9, 3),
            created_by=self.user,
        )
        SaleItem.objects.create(sale=sale, product=self.product, quantity='1.00', unit_price='20.00', unit_cost='10.00')
        sale.recalculate_totals()

        Payment.objects.create(sale=sale, amount='20.00', received_by=self.user)

        with self.assertRaises(ValidationError):
            Payment.objects.create(sale=sale, amount='1.00', received_by=self.user)

    def test_second_stale_expense_approval_is_rejected(self):
        expense = Expense.objects.create(
            organization=self.organization,
            branch=self.branch,
            category=self.category,
            title='Concurrent Approval',
            amount='50.00',
            expense_date=date(2026, 9, 3),
            created_by=self.user,
        )
        stale_expense = Expense.objects.get(pk=expense.pk)

        expense.approve(self.user)

        with self.assertRaises(ValidationError):
            stale_expense.approve(self.user)
