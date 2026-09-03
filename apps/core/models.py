from django.db import models
from django.utils import timezone


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='deleted_%(class)ss',
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if getattr(user, 'is_authenticated', False):
            self.deleted_by = user
        update_fields = ['is_deleted', 'deleted_at', 'deleted_by']
        if hasattr(self, 'is_active'):
            self.is_active = False
            update_fields.append('is_active')
        self.save(update_fields=update_fields)
