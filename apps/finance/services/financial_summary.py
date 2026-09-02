from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum

from apps.expenses.models import Expense
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Payment, Sale


ZERO = Decimal('0.00')


def decimal_sum(value):
    return value or ZERO


class FinancialSummaryService:
    def __init__(self, organization, date_from=None, date_to=None, branch=None):
        self.organization = organization
        self.date_from = date_from
        self.date_to = date_to
        self.branch = branch

    def get_sales_queryset(self):
        queryset = Sale.objects.filter(
            organization=self.organization,
            status=Sale.Status.COMPLETED,
        )
        if self.branch:
            queryset = queryset.filter(branch=self.branch)
        if self.date_from:
            queryset = queryset.filter(sale_date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(sale_date__lte=self.date_to)
        return queryset

    def get_payment_queryset(self):
        queryset = Payment.objects.filter(organization=self.organization)
        if self.branch:
            queryset = queryset.filter(sale__branch=self.branch)
        if self.date_from:
            queryset = queryset.filter(paid_at__date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(paid_at__date__lte=self.date_to)
        return queryset

    def get_expense_queryset(self):
        queryset = Expense.objects.filter(
            organization=self.organization,
            status=Expense.Status.APPROVED,
        )
        if self.branch:
            queryset = queryset.filter(branch=self.branch)
        if self.date_from:
            queryset = queryset.filter(expense_date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(expense_date__lte=self.date_to)
        return queryset

    def get_purchase_queryset(self):
        queryset = Purchase.objects.filter(
            organization=self.organization,
            status=Purchase.Status.RECEIVED,
        )
        if self.branch:
            queryset = queryset.filter(branch=self.branch)
        if self.date_from:
            queryset = queryset.filter(order_date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(order_date__lte=self.date_to)
        return queryset

    def get_sales_summary(self):
        queryset = self.get_sales_queryset()
        totals = queryset.aggregate(
            revenue=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
            sales_count=Count('id'),
        )
        return {
            'revenue': decimal_sum(totals['revenue']),
            'sales_count': totals['sales_count'],
        }

    def get_payment_summary(self):
        received = decimal_sum(
            self.get_payment_queryset().aggregate(
                total=Sum('amount', output_field=DecimalField(max_digits=14, decimal_places=2))
            )['total']
        )
        revenue = self.get_sales_summary()['revenue']
        outstanding = revenue - received
        return {
            'received': received,
            'outstanding': max(outstanding, ZERO),
        }

    def get_expense_summary(self):
        queryset = self.get_expense_queryset()
        totals = queryset.aggregate(
            total=Sum('amount', output_field=DecimalField(max_digits=14, decimal_places=2)),
            expense_count=Count('id'),
        )
        return {
            'total': decimal_sum(totals['total']),
            'expense_count': totals['expense_count'],
        }

    def get_purchase_summary(self):
        queryset = self.get_purchase_queryset()
        purchase_total = queryset.aggregate(
            total=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
            purchase_count=Count('id'),
        )
        legacy_total = PurchaseItem.objects.filter(purchase__in=queryset).aggregate(
            total=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField(max_digits=14, decimal_places=2))
        )['total']
        return {
            'total': decimal_sum(purchase_total['total']) or decimal_sum(legacy_total),
            'purchase_count': purchase_total['purchase_count'],
        }

    def get_profit_summary(self):
        return {
            'revenue': self.get_sales_summary()['revenue'],
            'cost_of_goods_sold': ZERO,
            'gross_profit': self.get_sales_summary()['revenue'],
        }

    def get_cash_flow_summary(self):
        return {
            'cash_in': self.get_payment_summary()['received'],
            'cash_out': self.get_expense_summary()['total'],
            'net_cash_flow': ZERO,
        }

    def get_summary(self):
        return {
            'sales': self.get_sales_summary(),
            'payments': self.get_payment_summary(),
            'expenses': self.get_expense_summary(),
            'purchases': self.get_purchase_summary(),
            'profit': self.get_profit_summary(),
            'cash_flow': self.get_cash_flow_summary(),
        }
