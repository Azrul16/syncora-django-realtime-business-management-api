from django.db import models


class ExpenseCategory(models.Model):
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
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_expense_category_name_per_organization',
            ),
        ]

    def __str__(self):
        return self.name


class Expense(models.Model):
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
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f'{self.title} - {self.amount}'
