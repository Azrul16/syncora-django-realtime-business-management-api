from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('id', 'organization', 'branch', 'customer', 'status', 'created_at')
    list_filter = ('status', 'organization', 'branch')
    search_fields = ('reference', 'customer__name', 'branch__name', 'organization__name')


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price')
    search_fields = ('sale__reference', 'product__name', 'product__sku')
