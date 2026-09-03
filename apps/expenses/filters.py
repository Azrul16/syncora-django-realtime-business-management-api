import django_filters

from .models import Expense


class ExpenseFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='expense_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='expense_date', lookup_expr='lte')

    class Meta:
        model = Expense
        fields = ['organization', 'branch', 'category', 'status', 'expense_date', 'date_from', 'date_to']
