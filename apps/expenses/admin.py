from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'branch', 'category', 'amount', 'expense_date')
    list_filter = ('category', 'organization', 'branch', 'expense_date')
    search_fields = ('title', 'notes', 'organization__name', 'branch__name')
