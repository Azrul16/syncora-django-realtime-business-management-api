from decimal import Decimal

from django.db import models, transaction


class Sale(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='sales',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='sales',
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='sales',
        null=True,
        blank=True,
    )
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0'))

    @transaction.atomic
    def complete(self):
        from apps.inventory.models import StockMovement
        from apps.inventory.services import decrease_stock
        from django.core.exceptions import ValidationError
        from django.utils import timezone

        if self.status == self.Status.COMPLETED:
            return

        for item in self.items.select_related('product'):
            try:
                decrease_stock(
                    branch=self.branch,
                    product_variant=item.product_variant,
                    product=item.product,
                    quantity=item.quantity,
                    movement_type=StockMovement.MovementType.SALE,
                    reference=self.reference,
                    note='Sale completed.',
                )
            except ValidationError:
                raise ValidationError(f'Insufficient stock for {item.product}.')

        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def __str__(self):
        return self.reference or f'Sale #{self.pk}'


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='sale_items',
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.PROTECT,
        related_name='sale_items',
        null=True,
        blank=True,
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.product} x {self.quantity}'
