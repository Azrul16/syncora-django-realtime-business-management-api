from django.contrib import admin

from .models import InventoryStock, StockMovement


@admin.register(InventoryStock)
class InventoryStockAdmin(admin.ModelAdmin):
    list_display = ('product_variant', 'product', 'branch', 'organization', 'quantity', 'reorder_level', 'updated_at')
    list_filter = ('organization', 'branch')
    search_fields = ('product_variant__name', 'product__name', 'product__sku', 'branch__name', 'organization__name')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'movement_type',
        'product_variant',
        'product',
        'branch',
        'quantity',
        'previous_quantity',
        'new_quantity',
        'created_at',
    )
    list_filter = ('movement_type', 'organization', 'branch')
    search_fields = ('product_variant__name', 'product__name', 'product__sku', 'reference', 'note')
