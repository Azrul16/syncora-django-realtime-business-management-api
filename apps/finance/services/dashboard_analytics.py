from datetime import timedelta

from django.db.models import Avg, Case, Count, DecimalField, F, Max, Sum, When
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

from apps.customers.models import Customer
from apps.inventory.models import InventoryStock
from apps.branches.models import Branch
from apps.products.models import Product
from apps.sales.models import Payment, SaleItem

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
        trunc = self.get_trunc_function(granularity)
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

    def get_profit_trend(self, granularity='day'):
        trunc = self.get_trunc_function(granularity)
        revenue_rows = self.financials.get_sales_queryset().annotate(
            period=trunc('sale_date')
        ).values('period').annotate(
            revenue=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
        cogs_rows = SaleItem.objects.filter(sale__in=self.financials.get_sales_queryset()).annotate(
            period=trunc('sale__sale_date')
        ).values('period').annotate(
            cogs=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
        revenue_by_period = {row['period']: decimal_sum(row['revenue']) for row in revenue_rows}
        cogs_by_period = {row['period']: decimal_sum(row['cogs']) for row in cogs_rows}

        rows = []
        for period in sorted(set(revenue_by_period) | set(cogs_by_period)):
            revenue = revenue_by_period.get(period, decimal_sum(None))
            cogs = cogs_by_period.get(period, decimal_sum(None))
            gross_profit = revenue - cogs
            margin = (gross_profit / revenue * 100) if revenue else decimal_sum(None)
            rows.append(
                {
                    'date': (period.date() if hasattr(period, 'date') else period).isoformat(),
                    'revenue': revenue,
                    'cogs': cogs,
                    'gross_profit': gross_profit,
                    'gross_margin_percentage': margin,
                }
            )
        return rows

    def get_trunc_function(self, granularity):
        return {
            'week': TruncWeek,
            'month': TruncMonth,
        }.get(granularity, TruncDay)

    def get_top_products(self, limit=10):
        queryset = SaleItem.objects.filter(sale__in=self.financials.get_sales_queryset())
        return [
            {
                'product_id': row['product_id'],
                'product': row['product__name'],
                'quantity_sold': decimal_sum(row['quantity_sold']),
                'revenue': decimal_sum(row['revenue']),
                'profit': decimal_sum(row['profit']),
                'average_selling_price': decimal_sum(row['average_selling_price']),
                'last_sold_date': row['last_sold_date'].isoformat() if row['last_sold_date'] else None,
            }
            for row in queryset.values('product_id', 'product__name')
            .annotate(
                quantity_sold=Sum('quantity', output_field=DecimalField(max_digits=14, decimal_places=2)),
                revenue=Sum(F('quantity') * F('unit_price'), output_field=DecimalField(max_digits=14, decimal_places=2)),
                profit=Sum(
                    F('quantity') * (F('unit_price') - F('unit_cost')),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                average_selling_price=Avg('unit_price', output_field=DecimalField(max_digits=14, decimal_places=2)),
                last_sold_date=Max('sale__sale_date'),
            )
            .order_by('-quantity_sold', '-revenue')[:limit]
        ]

    def get_slow_moving_products(self, days=30, limit=10):
        cutoff = timezone.localdate() - timedelta(days=days)
        recent_product_ids = SaleItem.objects.filter(
            sale__organization=self.organization,
            sale__status='COMPLETED',
            sale__sale_date__gte=cutoff,
        ).values_list('product_id', flat=True)
        stocked_product_ids = self.get_inventory_queryset().filter(
            quantity__gt=0
        ).values_list('product_id', flat=True)
        products = Product.objects.filter(
            organization=self.organization,
            id__in=stocked_product_ids,
            is_active=True,
        ).exclude(id__in=recent_product_ids)
        return [
            {
                'product_id': product.id,
                'product': product.name,
                'sku': product.sku,
            }
            for product in products.order_by('name')[:limit]
        ]

    def get_inventory_summary(self):
        inventory = self.get_inventory_queryset()
        valued_inventory = inventory.annotate(
            cost_price=Case(
                When(product_variant__isnull=False, then=F('product_variant__cost_price')),
                default=F('product__cost_price'),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            sale_price=Case(
                When(product_variant__isnull=False, then=F('product_variant__selling_price')),
                default=F('product__selling_price'),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )
        totals = valued_inventory.aggregate(
            total_units=Sum('quantity', output_field=DecimalField(max_digits=14, decimal_places=2)),
            inventory_cost_value=Sum(
                F('quantity') * F('cost_price'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            potential_sale_value=Sum(
                F('quantity') * F('sale_price'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        return {
            'total_units': decimal_sum(totals['total_units']),
            'inventory_cost_value': decimal_sum(totals['inventory_cost_value']),
            'potential_sale_value': decimal_sum(totals['potential_sale_value']),
            'low_stock_products': inventory.filter(quantity__lte=F('reorder_level')).count(),
            'out_of_stock_products': inventory.filter(quantity__lte=0).count(),
        }

    def get_low_stock_items(self, limit=20):
        return self.serialize_inventory_items(
            self.get_inventory_queryset().filter(quantity__lte=F('reorder_level')).order_by('quantity')[:limit]
        )

    def get_out_of_stock_items(self, limit=20):
        return self.serialize_inventory_items(
            self.get_inventory_queryset().filter(quantity__lte=0).order_by('product__name')[:limit]
        )

    def get_stock_value(self):
        summary = self.get_inventory_summary()
        return {
            'inventory_cost_value': summary['inventory_cost_value'],
            'potential_sale_value': summary['potential_sale_value'],
        }

    def serialize_inventory_items(self, items):
        return [
            {
                'inventory_id': item.id,
                'branch_id': item.branch_id,
                'product_id': item.product_id,
                'product': item.product.name,
                'variant_id': item.product_variant_id,
                'variant': item.product_variant.name if item.product_variant else '',
                'quantity': item.quantity,
                'reorder_level': item.reorder_level,
            }
            for item in items
        ]

    def get_branch_performance(self):
        branch_queryset = Branch.objects.filter(organization=self.organization, is_active=True)
        if self.branch:
            branch_queryset = branch_queryset.filter(id=self.branch.id)

        sales_rows = self.financials.get_sales_queryset().values('branch_id').annotate(
            revenue=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
            sales_count=Count('id'),
        )
        cogs_rows = SaleItem.objects.filter(sale__in=self.financials.get_sales_queryset()).values(
            'sale__branch_id'
        ).annotate(
            cogs=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
        low_stock_rows = InventoryStock.objects.filter(
            organization=self.organization,
            quantity__lte=F('reorder_level'),
        ).values('branch_id').annotate(low_stock=Count('id'))
        sales_by_branch = {row['branch_id']: row for row in sales_rows}
        cogs_by_branch = {row['sale__branch_id']: decimal_sum(row['cogs']) for row in cogs_rows}
        low_stock_by_branch = {row['branch_id']: row['low_stock'] for row in low_stock_rows}

        rows = []
        for branch in branch_queryset:
            sales = sales_by_branch.get(branch.id, {})
            revenue = decimal_sum(sales.get('revenue'))
            cogs = cogs_by_branch.get(branch.id, decimal_sum(None))
            rows.append(
                {
                    'branch_id': branch.id,
                    'branch': branch.name,
                    'revenue': revenue,
                    'cost_of_goods_sold': cogs,
                    'gross_profit': revenue - cogs,
                    'sales_count': sales.get('sales_count', 0),
                    'low_stock': low_stock_by_branch.get(branch.id, 0),
                }
            )
        return sorted(rows, key=lambda row: (row['revenue'], row['gross_profit']), reverse=True)

    def get_customer_analytics(self, limit=10):
        sales = self.financials.get_sales_queryset().filter(customer__isnull=False)
        customer_rows = sales.values('customer_id', 'customer__name').annotate(
            total_spent=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
            orders=Count('id'),
            last_purchase=Max('sale_date'),
        ).order_by('-total_spent')[:limit]
        totals = sales.aggregate(
            total_spend=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
            order_count=Count('id'),
        )
        repeat_customers = sales.values('customer_id').annotate(orders=Count('id')).filter(orders__gt=1).count()
        customer_count = Customer.objects.filter(organization=self.organization, is_active=True).count()
        average_spend = decimal_sum(totals['total_spend']) / customer_count if customer_count else decimal_sum(None)

        return {
            'total_customers': customer_count,
            'new_customers': self.get_customer_queryset().count(),
            'repeat_customers': repeat_customers,
            'average_customer_spend': average_spend,
            'outstanding_due': self.financials.get_payment_summary()['outstanding'],
            'top_customers': [
                {
                    'customer_id': row['customer_id'],
                    'customer': row['customer__name'],
                    'total_spent': decimal_sum(row['total_spent']),
                    'orders': row['orders'],
                    'last_purchase': row['last_purchase'].isoformat() if row['last_purchase'] else None,
                }
                for row in customer_rows
            ],
        }

    def get_customer_summary(self, customer):
        sales = self.financials.get_sales_queryset().filter(customer=customer)
        totals = sales.aggregate(
            total_spent=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)),
            total_orders=Count('id'),
            last_purchase=Max('sale_date'),
        )
        total_paid = decimal_sum(
            Payment.objects.filter(sale__in=sales).aggregate(
                total=Sum('amount', output_field=DecimalField(max_digits=14, decimal_places=2))
            )['total']
        )
        total_spent = decimal_sum(totals['total_spent'])
        return {
            'customer_id': customer.id,
            'customer': customer.name,
            'total_orders': totals['total_orders'],
            'total_spent': total_spent,
            'total_paid': total_paid,
            'outstanding_due': max(total_spent - total_paid, decimal_sum(None)),
            'last_purchase': totals['last_purchase'].isoformat() if totals['last_purchase'] else None,
        }
