import django_filters

from .models import Sale


class SaleFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='sale_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='sale_date', lookup_expr='lte')

    class Meta:
        model = Sale
        fields = ['organization', 'branch', 'customer', 'status', 'date_from', 'date_to']
