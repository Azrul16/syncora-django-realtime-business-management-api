from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum

from apps.expenses.models import Expense
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Payment, Sale, SaleItem


ZERO = Decimal('0.00')


def decimal_sum(value):
    return value or ZERO


class FinancialSummaryService:
    def __init__(self, organization, date_from=None, date_to=None, branch=None, branch_ids=None):
        self.organization = organization
        self.date_from = date_from
        self.date_to = date_to
        self.branch = branch
        self.branch_ids = branch_ids

    def filter_by_branch_scope(self, queryset, field='branch'):
        if self.branch:
            return queryset.filter(**{field: self.branch})
        if self.branch_ids is not None:
            return queryset.filter(**{f'{field}_id__in': self.branch_ids})
        return queryset

    def get_sales_queryset(self):
        queryset = Sale.objects.filter(
            organization=self.organization,
            status=Sale.Status.COMPLETED,
        )
        queryset = self.filter_by_branch_scope(queryset)
        if self.date_from:
            queryset = queryset.filter(sale_date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(sale_date__lte=self.date_to)
        return queryset

    def get_payment_queryset(self):
        queryset = Payment.objects.filter(organization=self.organization)
        queryset = self.filter_by_branch_scope(queryset, field='sale__branch')
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
        queryset = self.filter_by_branch_scope(queryset)
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
        queryset = self.filter_by_branch_scope(queryset)
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
        sales = self.get_sales_queryset()
        revenue = self.get_sales_summary()['revenue']
        cogs = decimal_sum(
            SaleItem.objects.filter(sale__in=sales).aggregate(
                total=Sum(
                    F('quantity') * F('unit_cost'),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )['total']
        )
        return {
            'revenue': revenue,
            'cost_of_goods_sold': cogs,
            'gross_profit': revenue - cogs,
        }

    def get_cash_flow_summary(self):
        cash_in = self.get_payment_summary()['received']
        cash_out = self.get_expense_summary()['total']
        return {
            'cash_in': cash_in,
            'cash_out': cash_out,
            'net_cash_flow': cash_in - cash_out,
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
