from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import F
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import InventoryStock, StockMovement
from .serializers import InventoryStockSerializer, StockMovementSerializer
from .services import decrease_stock, increase_stock


class InventoryStockViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryStockSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'product']
    search_fields = ['product__name', 'product__sku', 'branch__name']
    ordering_fields = ['quantity', 'updated_at']

    def get_queryset(self):
        queryset = InventoryStock.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'product').distinct()
        if self.request.query_params.get('low_stock') in {'1', 'true', 'True'}:
            queryset = queryset.filter(quantity__lte=F('reorder_level'))
        return queryset

    def perform_create(self, serializer):
        organization = serializer.validated_data['branch'].organization
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create stock records.')
        serializer.save()

    @action(detail=True, methods=['post'])
    def increase(self, request, pk=None):
        return self.change_quantity(request, self.get_object(), increase_stock)

    @action(detail=True, methods=['post'])
    def decrease(self, request, pk=None):
        return self.change_quantity(request, self.get_object(), decrease_stock)

    def change_quantity(self, request, stock, service):
        membership = get_active_membership(request.user, stock.organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can adjust stock.')
        quantity = request.data.get('quantity')
        if quantity is None:
            raise ValidationError({'quantity': 'This field is required.'})
        try:
            stock, _ = service(
                branch=stock.branch,
                product_variant=stock.product_variant,
                product=stock.product,
                quantity=quantity,
                reference=request.data.get('reference', 'inventory-api'),
                note=request.data.get('note', ''),
                user=request.user,
            )
        except DjangoValidationError as error:
            raise ValidationError({'quantity': error.messages}) from error
        return Response(self.get_serializer(stock).data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'product', 'product_variant', 'movement_type']
    search_fields = ['reference', 'note', 'product__name', 'product_variant__name']
    ordering_fields = ['created_at', 'quantity']

    def get_queryset(self):
        return StockMovement.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'product', 'product_variant').distinct()
