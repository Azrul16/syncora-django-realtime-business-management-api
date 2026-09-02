from django.db import models
from django.utils.text import slugify


class Product(models.Model):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='products',
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    sku = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, default='pcs')
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
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
