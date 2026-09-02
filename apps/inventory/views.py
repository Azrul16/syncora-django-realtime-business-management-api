from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import InventoryStock
from .serializers import InventoryStockSerializer


class InventoryStockViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryStockSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'product']
    search_fields = ['product__name', 'product__sku', 'branch__name']
    ordering_fields = ['quantity', 'updated_at']

    def get_queryset(self):
        return InventoryStock.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'product').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['branch'].organization
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create stock records.')
        serializer.save()
