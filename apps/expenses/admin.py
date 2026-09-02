from django.contrib import admin

from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active', 'created_at')
    list_filter = ('is_active', 'organization')
    search_fields = ('name', 'description', 'organization__name')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'branch', 'category', 'amount', 'expense_date')
    list_filter = ('category', 'organization', 'branch', 'expense_date')
    search_fields = ('title', 'notes', 'organization__name', 'branch__name')
