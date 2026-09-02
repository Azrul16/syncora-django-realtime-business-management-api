from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import Sale
from .serializers import SaleSerializer


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'customer', 'status']
    search_fields = ['reference', 'customer__name', 'branch__name']
    ordering_fields = ['created_at', 'updated_at', 'completed_at']

    def get_queryset(self):
        return Sale.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'customer').prefetch_related('items__product').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['branch'].organization
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create sales.')
        serializer.save()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        sale = self.get_object()
        membership = get_active_membership(request.user, sale.organization)

        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can complete sales.')
        if sale.status == Sale.Status.CANCELLED:
            raise ValidationError({'status': 'Cancelled sales cannot be completed.'})

        serializer = self.get_serializer()
        serializer.complete(sale)
        return Response(self.get_serializer(sale).data, status=status.HTTP_200_OK)
