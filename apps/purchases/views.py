from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import Purchase
from .serializers import PurchaseSerializer


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'supplier', 'status']
    search_fields = ['reference', 'supplier__name', 'branch__name']
    ordering_fields = ['created_at', 'updated_at', 'received_at']

    def get_queryset(self):
        return Purchase.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'supplier').prefetch_related('items__product').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['branch'].organization
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create purchases.')
        serializer.save()

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        purchase = self.get_object()
        membership = get_active_membership(request.user, purchase.organization)

        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can receive purchases.')
        if purchase.status == Purchase.Status.CANCELLED:
            raise ValidationError({'status': 'Cancelled purchases cannot be received.'})

        purchase.receive()
        serializer = self.get_serializer(purchase)
        return Response(serializer.data, status=status.HTTP_200_OK)
