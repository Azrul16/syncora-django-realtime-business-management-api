from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'organization', 'selling_price', 'is_active')
    list_filter = ('is_active', 'organization')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'sku', 'organization__name')
