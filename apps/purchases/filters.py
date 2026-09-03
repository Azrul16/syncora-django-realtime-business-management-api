import django_filters

from .models import Purchase


class PurchaseFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')

    class Meta:
        model = Purchase
        fields = ['organization', 'branch', 'supplier', 'status', 'date_from', 'date_to']
