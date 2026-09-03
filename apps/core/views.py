class SoftDeleteViewSetMixin:
    def perform_destroy(self, instance):
        instance.soft_delete(self.request.user)
