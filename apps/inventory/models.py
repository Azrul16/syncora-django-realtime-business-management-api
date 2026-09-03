from django.db import models


class InventoryStock(models.Model):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='inventory_stocks',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='inventory_stocks',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='inventory_stocks',
        null=True,
        blank=True,
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        related_name='inventory_stocks',
        null=True,
        blank=True,
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='updated_inventory_stocks',
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'branch', 'product_variant', 'product']
        indexes = [
            models.Index(fields=['organization', 'branch']),
            models.Index(fields=['organization', 'product']),
            models.Index(fields=['organization', 'product_variant']),
            models.Index(fields=['branch', 'updated_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['branch', 'product'],
                condition=models.Q(product_variant__isnull=True),
                name='unique_inventory_stock_per_branch_product',
            ),
            models.UniqueConstraint(
                fields=['branch', 'product_variant'],
                name='unique_inventory_stock_per_branch_variant',
            ),
        ]

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    def __str__(self):
        item = self.product_variant or self.product
        return f'{item} at {self.branch}: {self.quantity}'


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        OPENING_STOCK = 'OPENING_STOCK', 'Opening stock'
        PURCHASE = 'PURCHASE', 'Purchase'
        SALE = 'SALE', 'Sale'
        ADJUSTMENT_IN = 'ADJUSTMENT_IN', 'Adjustment in'
        ADJUSTMENT_OUT = 'ADJUSTMENT_OUT', 'Adjustment out'
        TRANSFER_IN = 'TRANSFER_IN', 'Transfer in'
        TRANSFER_OUT = 'TRANSFER_OUT', 'Transfer out'
        RETURN_IN = 'RETURN_IN', 'Return in'
        RETURN_OUT = 'RETURN_OUT', 'Return out'

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        related_name='stock_movements',
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stock_movements',
        null=True,
        blank=True,
    )
    movement_type = models.CharField(max_length=30, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    previous_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    new_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='created_stock_movements',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['organization', 'branch', '-created_at']),
            models.Index(fields=['organization', 'movement_type', '-created_at']),
            models.Index(fields=['reference']),
        ]

    def __str__(self):
        item = self.product_variant or self.product
        return f'{self.movement_type}: {item} {self.previous_quantity} -> {self.new_quantity}'
