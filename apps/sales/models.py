from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class Sale(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'UNPAID', 'Unpaid'
        PARTIALLY_PAID = 'PARTIALLY_PAID', 'Partially paid'
        PAID = 'PAID', 'Paid'

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
    sale_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    sale_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='created_sales',
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def total_amount(self):
        return self.grand_total

    @property
    def paid_amount(self):
        return sum((payment.amount for payment in self.payments.all()), Decimal('0'))

    @property
    def due_amount(self):
        due = self.grand_total - self.paid_amount
        return max(due, Decimal('0'))

    @property
    def payment_status(self):
        paid = self.paid_amount
        if paid <= 0:
            return self.PaymentStatus.UNPAID
        if paid < self.grand_total:
            return self.PaymentStatus.PARTIALLY_PAID
        return self.PaymentStatus.PAID

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.sale_number:
            self.sale_number = f'SL-{self.pk:06d}'
            super().save(update_fields=['sale_number'])

    def recalculate_totals(self):
        self.subtotal = sum((item.line_total for item in self.items.all()), Decimal('0'))
        self.grand_total = self.subtotal - self.discount_amount + self.tax_amount
        self.save(update_fields=['subtotal', 'grand_total', 'updated_at'])

    def confirm(self):
        if self.status != self.Status.DRAFT:
            raise ValidationError('Only draft sales can be confirmed.')
        if not self.items.exists():
            raise ValidationError('Sale must have at least one item before confirming.')
        self.status = self.Status.CONFIRMED
        self.save(update_fields=['status', 'updated_at'])

    def cancel(self):
        if self.status == self.Status.COMPLETED:
            raise ValidationError('Completed sales cannot be cancelled.')
        if self.status == self.Status.CANCELLED:
            raise ValidationError('Sale is already cancelled.')
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    @transaction.atomic
    def complete(self):
        from apps.inventory.models import StockMovement
        from apps.inventory.services import decrease_stock
        from django.core.exceptions import ValidationError
        from django.utils import timezone

        if self.status == self.Status.COMPLETED:
            raise ValidationError('Sale is already completed.')
        if self.status != self.Status.CONFIRMED:
            raise ValidationError('Only confirmed sales can be completed.')

        for item in self.items.select_related('product'):
            try:
                decrease_stock(
                    branch=self.branch,
                    product_variant=item.product_variant,
                    product=item.product,
                    quantity=item.quantity,
                    movement_type=StockMovement.MovementType.SALE,
                    reference=self.sale_number or self.reference,
                    note='Sale completed.',
                    user=self.created_by,
                )
            except ValidationError:
                raise ValidationError(f'Insufficient stock for {item.product}.')

        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def __str__(self):
        return self.sale_number or self.reference or f'Sale #{self.pk}'


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
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return (self.quantity * self.unit_price) - self.discount + self.tax

    def __str__(self):
        return f'{self.product} x {self.quantity}'


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Card'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank transfer'
        MOBILE_BANKING = 'MOBILE_BANKING', 'Mobile banking'
        OTHER = 'OTHER', 'Other'

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=Method.choices, default=Method.CASH)
    reference_number = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)
    received_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='received_payments',
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_at']

    def clean(self):
        if self.amount <= 0:
            raise ValidationError('Payment amount must be greater than zero.')
        existing_paid = self.sale.payments.exclude(pk=self.pk).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        if existing_paid + self.amount > self.sale.grand_total:
            raise ValidationError('Payment amount cannot exceed sale due amount.')

    def save(self, *args, **kwargs):
        self.organization = self.sale.organization
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.sale} - {self.amount}'
