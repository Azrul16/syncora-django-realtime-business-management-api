from django.db import models

from apps.core.models import SoftDeleteModel


class ExpenseCategory(SoftDeleteModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='expense_categories',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'is_active', 'is_deleted']),
            models.Index(fields=['organization', 'name']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_expense_category_name_per_organization',
            ),
        ]

    def __str__(self):
        return self.name


class Expense(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class Category(models.TextChoices):
        RENT = 'RENT', 'Rent'
        SALARY = 'SALARY', 'Salary'
        UTILITIES = 'UTILITIES', 'Utilities'
        TRANSPORT = 'TRANSPORT', 'Transport'
        SUPPLIES = 'SUPPLIES', 'Supplies'
        OTHER = 'OTHER', 'Other'

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='expenses',
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        null=True,
        blank=True,
    )
    legacy_category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    expense_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='created_expenses',
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='approved_expenses',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'branch']),
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'expense_date']),
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['expense_number']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.expense_number:
            self.expense_number = f'EXP-{self.pk:06d}'
            super().save(update_fields=['expense_number'])

    def approve(self, user):
        from django.core.exceptions import ValidationError

        if self.status != self.Status.DRAFT:
            raise ValidationError('Only draft expenses can be approved.')
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.save(update_fields=['status', 'approved_by', 'updated_at'])

    def reject(self, user):
        from django.core.exceptions import ValidationError

        if self.status != self.Status.DRAFT:
            raise ValidationError('Only draft expenses can be rejected.')
        self.status = self.Status.REJECTED
        self.approved_by = user
        self.save(update_fields=['status', 'approved_by', 'updated_at'])

    def cancel(self):
        from django.core.exceptions import ValidationError

        if self.status != self.Status.DRAFT:
            raise ValidationError('Only draft expenses can be cancelled.')
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f'{self.expense_number or self.title} - {self.amount}'
