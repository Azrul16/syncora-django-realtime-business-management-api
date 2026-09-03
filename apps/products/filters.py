import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='category_id')
    brand = django_filters.CharFilter(field_name='brand', lookup_expr='iexact')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Product
        fields = ['organization', 'category', 'brand', 'is_active', 'sku']
