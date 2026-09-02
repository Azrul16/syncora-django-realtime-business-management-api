from decimal import Decimal

from django.db import models, transaction


class Purchase(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        RECEIVED = 'RECEIVED', 'Received'
        CANCELLED = 'CANCELLED', 'Cancelled'

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='purchases',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='purchases',
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.PROTECT,
        related_name='purchases',
    )
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0'))

    @transaction.atomic
    def receive(self):
        from apps.inventory.services import increase_stock
        from apps.inventory.models import StockMovement
        from django.utils import timezone

        if self.status == self.Status.RECEIVED:
            return

        for item in self.items.select_related('product'):
            increase_stock(
                branch=self.branch,
                product_variant=item.product_variant,
                product=item.product,
                quantity=item.quantity,
                movement_type=StockMovement.MovementType.PURCHASE,
                reference=self.reference,
                note='Purchase received.',
            )

        self.status = self.Status.RECEIVED
        self.received_at = timezone.now()
        self.save(update_fields=['status', 'received_at', 'updated_at'])

    def __str__(self):
        return self.reference or f'Purchase #{self.pk}'


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='purchase_items',
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.PROTECT,
        related_name='purchase_items',
        null=True,
        blank=True,
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f'{self.product} x {self.quantity}'
