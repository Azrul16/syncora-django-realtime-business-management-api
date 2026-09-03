from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek

from apps.customers.models import Customer
from apps.inventory.models import InventoryStock
from apps.products.models import Product

from .financial_summary import FinancialSummaryService, decimal_sum


class DashboardAnalyticsService:
    def __init__(self, organization, date_from=None, date_to=None, branch=None):
        self.organization = organization
        self.date_from = date_from
        self.date_to = date_to
        self.branch = branch
        self.financials = FinancialSummaryService(
            organization=organization,
            date_from=date_from,
            date_to=date_to,
            branch=branch,
        )

    def get_customer_queryset(self):
        queryset = Customer.objects.filter(organization=self.organization, is_active=True)
        if self.date_from:
            queryset = queryset.filter(created_at__date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(created_at__date__lte=self.date_to)
        return queryset

    def get_inventory_queryset(self):
        queryset = InventoryStock.objects.filter(organization=self.organization)
        if self.branch:
            queryset = queryset.filter(branch=self.branch)
        return queryset.select_related('product', 'product_variant')

    def get_summary(self):
        sales = self.financials.get_sales_summary()
        payments = self.financials.get_payment_summary()
        expenses = self.financials.get_expense_summary()
        profit = self.financials.get_profit_summary()
        inventory = self.get_inventory_queryset()
        inventory_totals = inventory.aggregate(
            total_units=Sum('quantity', output_field=DecimalField(max_digits=14, decimal_places=2)),
        )

        return {
            'today': {
                'revenue': sales['revenue'],
                'sales_count': sales['sales_count'],
                'gross_profit': profit['gross_profit'],
                'cash_received': payments['received'],
                'expenses': expenses['total'],
            },
            'inventory': {
                'total_products': Product.objects.filter(
                    organization=self.organization,
                    is_active=True,
                ).count(),
                'total_units': decimal_sum(inventory_totals['total_units']),
                'low_stock': inventory.filter(quantity__lte=F('reorder_level')).count(),
                'out_of_stock': inventory.filter(quantity__lte=0).count(),
            },
            'customers': {
                'total': Customer.objects.filter(organization=self.organization, is_active=True).count(),
                'new': self.get_customer_queryset().count(),
            },
        }

    def get_sales_trend(self, granularity='day'):
        trunc = {
            'week': TruncWeek,
            'month': TruncMonth,
        }.get(granularity, TruncDay)
        rows = (
            self.financials.get_sales_queryset()
            .annotate(period=trunc('sale_date'))
            .values('period')
            .annotate(
                sales_count=Count('id'),
                revenue=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
            .order_by('period')
        )
        return [
            {
                'date': (row['period'].date() if hasattr(row['period'], 'date') else row['period']).isoformat(),
                'sales_count': row['sales_count'],
                'revenue': decimal_sum(row['revenue']),
            }
            for row in rows
        ]
