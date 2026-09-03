from django.db import models
from django.utils.text import slugify

from apps.core.models import SoftDeleteModel


class Branch(SoftDeleteModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='branches',
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_branch_slug_per_organization',
            ),
            models.UniqueConstraint(
                fields=['organization', 'code'],
                condition=models.Q(code__gt=''),
                name='unique_branch_code_per_organization',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.organization})'
