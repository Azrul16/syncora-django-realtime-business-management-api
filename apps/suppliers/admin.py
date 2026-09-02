from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'organization')
    search_fields = ('name', 'email', 'phone', 'organization__name')
