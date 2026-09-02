from django.contrib import admin

from .models import Payment, Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('sale_number', 'organization', 'branch', 'customer', 'status', 'grand_total', 'created_at')
    list_filter = ('status', 'organization', 'branch')
    search_fields = ('reference', 'customer__name', 'branch__name', 'organization__name')


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price')
    search_fields = ('sale__reference', 'product__name', 'product__sku')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('sale', 'organization', 'amount', 'payment_method', 'paid_at', 'received_by')
    list_filter = ('payment_method', 'organization', 'paid_at')
    search_fields = ('sale__sale_number', 'reference_number', 'notes')
