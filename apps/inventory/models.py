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
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'branch', 'product']
        constraints = [
            models.UniqueConstraint(
                fields=['branch', 'product'],
                name='unique_inventory_stock_per_branch_product',
            ),
        ]

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    def __str__(self):
        return f'{self.product} at {self.branch}: {self.quantity}'
