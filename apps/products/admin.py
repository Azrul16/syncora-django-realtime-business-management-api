from django.contrib import admin

from .models import Product, ProductCategory, ProductVariant


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active', 'created_at')
    list_filter = ('is_active', 'organization')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'organization__name')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductVariantInline]
    list_display = ('name', 'sku', 'organization', 'category', 'brand', 'selling_price', 'is_active')
    list_filter = ('is_active', 'organization', 'category')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'sku', 'brand', 'organization__name')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'product', 'selling_price', 'is_active')
    list_filter = ('is_active', 'product__organization')
    search_fields = ('name', 'sku', 'product__name')
