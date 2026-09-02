from django.contrib import admin

from .models import Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    inlines = [PurchaseItemInline]
    list_display = ('id', 'organization', 'branch', 'supplier', 'status', 'created_at')
    list_filter = ('status', 'organization', 'branch')
    search_fields = ('reference', 'supplier__name', 'branch__name', 'organization__name')


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'product', 'quantity', 'unit_cost')
    search_fields = ('purchase__reference', 'product__name', 'product__sku')
