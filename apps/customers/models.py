from django.db import models

from apps.core.models import SoftDeleteModel


class Customer(SoftDeleteModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='customers',
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    customer_code = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='created_customers',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'customer_code'],
                condition=models.Q(customer_code__gt=''),
                name='unique_customer_code_per_organization',
            ),
        ]

    def __str__(self):
        return self.name
