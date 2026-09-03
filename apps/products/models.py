from django.db import models
from django.utils.text import slugify

from apps.core.models import SoftDeleteModel


class ProductCategory(SoftDeleteModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='product_categories',
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_product_category_name_per_organization',
            ),
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_product_category_slug_per_organization',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(SoftDeleteModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='products',
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    sku = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=50, default='pcs')
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='created_products',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'sku'],
                name='unique_product_sku_per_organization',
            ),
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_product_slug_per_organization',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.sku})'


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'sku'],
                name='unique_product_variant_sku_per_product',
            ),
        ]

    @property
    def organization(self):
        return self.product.organization

    def __str__(self):
        return f'{self.product.name} - {self.name}'
