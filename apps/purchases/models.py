from decimal import Decimal

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


class Purchase(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ORDERED = 'ORDERED', 'Ordered'
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
    purchase_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    order_date = models.DateField(default=timezone.localdate)
    expected_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='created_purchases',
        null=True,
        blank=True,
    )
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'branch']),
            models.Index(fields=['organization', 'supplier']),
            models.Index(fields=['organization', 'order_date']),
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['purchase_number']),
        ]

    @property
    def total_amount(self):
        return self.grand_total

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.purchase_number:
            self.purchase_number = f'PO-{self.pk:06d}'
            super().save(update_fields=['purchase_number'])

    def recalculate_totals(self):
        self.subtotal = sum((item.line_total for item in self.items.all()), Decimal('0'))
        self.grand_total = self.subtotal - self.discount_amount + self.tax_amount + self.shipping_cost
        self.save(update_fields=['subtotal', 'grand_total', 'updated_at'])

    def order(self):
        if self.status != self.Status.DRAFT:
            raise ValidationError('Only draft purchases can be ordered.')
        self.status = self.Status.ORDERED
        self.save(update_fields=['status', 'updated_at'])

    def cancel(self):
        if self.status == self.Status.RECEIVED:
            raise ValidationError('Received purchases cannot be cancelled.')
        if self.status == self.Status.CANCELLED:
            raise ValidationError('Purchase is already cancelled.')
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    @transaction.atomic
    def receive(self):
        from apps.inventory.models import StockMovement
        from apps.inventory.services import increase_stock
        from django.utils import timezone

        purchase = type(self).objects.select_for_update().prefetch_related(
            'items__product',
            'items__product_variant',
        ).get(pk=self.pk)

        if purchase.status == purchase.Status.RECEIVED:
            raise ValidationError('Purchase is already received.')
        if purchase.status != purchase.Status.ORDERED:
            raise ValidationError('Only ordered purchases can be received.')
        if not purchase.items.exists():
            raise ValidationError('Purchase must have at least one item before receiving.')

        for item in purchase.items.all():
            increase_stock(
                branch=purchase.branch,
                product_variant=item.product_variant,
                product=item.product,
                quantity=item.quantity,
                movement_type=StockMovement.MovementType.PURCHASE,
                reference=purchase.purchase_number or purchase.reference,
                note='Purchase received.',
                user=purchase.created_by,
            )

        purchase.status = purchase.Status.RECEIVED
        purchase.received_at = timezone.now()
        purchase.save(update_fields=['status', 'received_at', 'updated_at'])
        self.status = purchase.status
        self.received_at = purchase.received_at

    def __str__(self):
        return self.purchase_number or self.reference or f'Purchase #{self.pk}'


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
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['purchase', 'product']),
            models.Index(fields=['purchase', 'product_variant']),
        ]

    @property
    def line_total(self):
        return (self.quantity * self.unit_cost) - self.discount + self.tax

    def __str__(self):
        return f'{self.product} x {self.quantity}'
