from django.contrib import admin

from .models import InventoryStock


@admin.register(InventoryStock)
class InventoryStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'branch', 'organization', 'quantity', 'reorder_level', 'updated_at')
    list_filter = ('organization', 'branch')
    search_fields = ('product__name', 'product__sku', 'branch__name', 'organization__name')
