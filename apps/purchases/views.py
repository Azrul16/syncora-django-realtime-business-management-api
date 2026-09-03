from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.event_types import EventType
from apps.notifications.services.event_dispatcher import dispatch_event
from apps.organizations.models import OrganizationMembership
from apps.organizations.permissions import (
    IsOrganizationMember,
    enforce_permission,
    filter_queryset_by_branch_access,
    user_can_access_branch,
)

from .models import Purchase
from .filters import PurchaseFilter
from .serializers import PurchaseSerializer


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_class = PurchaseFilter
    search_fields = ['reference', 'purchase_number', 'supplier__name', 'branch__name']
    ordering_fields = ['order_date', 'created_at', 'updated_at', 'received_at']

    def get_queryset(self):
        queryset = Purchase.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'supplier', 'created_by').prefetch_related(
            'items__product',
            'items__product_variant',
        ).distinct()
        queryset = filter_queryset_by_branch_access(queryset, self.request.user)
        return queryset

    def perform_create(self, serializer):
        organization = serializer.validated_data['branch'].organization
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.PURCHASES_CREATE,
            'You do not have permission to create purchases.',
        )
        if not user_can_access_branch(self.request.user, organization, serializer.validated_data['branch']):
            raise PermissionDenied('You do not have access to this branch.')
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        enforce_permission(
            self.request.user,
            serializer.instance.organization,
            OrganizationMembership.Permission.PURCHASES_CREATE,
            'You do not have permission to manage purchases.',
        )
        if serializer.instance.status in {Purchase.Status.RECEIVED, Purchase.Status.CANCELLED}:
            raise ValidationError({'status': 'Received or cancelled purchases cannot be edited.'})
        purchase = serializer.save()
        purchase.recalculate_totals()

    @action(detail=True, methods=['post'])
    def order(self, request, pk=None):
        purchase = self.get_object()
        self.ensure_can_manage_purchase(request, purchase, 'order')

        try:
            purchase.order()
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.PURCHASE_ORDERED,
            organization=purchase.organization,
            actor=request.user,
            resource=purchase,
            branch=purchase.branch,
            data={'purchase_id': purchase.id, 'purchase_number': purchase.purchase_number, 'status': purchase.status},
            groups=[f'organization_{purchase.organization_id}_purchases'],
            activity_description=f'{purchase.purchase_number} was ordered.',
        )
        return Response(self.get_serializer(purchase).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        purchase = self.get_object()
        self.ensure_can_manage_purchase(request, purchase, 'receive')

        try:
            purchase.receive()
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.PURCHASE_RECEIVED,
            organization=purchase.organization,
            actor=request.user,
            resource=purchase,
            branch=purchase.branch,
            data={
                'purchase_id': purchase.id,
                'purchase_number': purchase.purchase_number,
                'status': purchase.status,
                'total': str(purchase.grand_total),
            },
            groups=[
                f'organization_{purchase.organization_id}_purchases',
                f'organization_{purchase.organization_id}_finance',
            ],
            notification_title='Purchase received',
            notification_message=f'{purchase.purchase_number} was received.',
            activity_description=f'{purchase.purchase_number} was received.',
        )
        serializer = self.get_serializer(purchase)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        purchase = self.get_object()
        self.ensure_can_manage_purchase(request, purchase, 'cancel')

        try:
            purchase.cancel()
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.PURCHASE_CANCELLED,
            organization=purchase.organization,
            actor=request.user,
            resource=purchase,
            branch=purchase.branch,
            data={'purchase_id': purchase.id, 'purchase_number': purchase.purchase_number, 'status': purchase.status},
            groups=[f'organization_{purchase.organization_id}_purchases'],
            activity_description=f'{purchase.purchase_number} was cancelled.',
        )
        return Response(self.get_serializer(purchase).data, status=status.HTTP_200_OK)

    def ensure_can_manage_purchase(self, request, purchase, action_name):
        permission = OrganizationMembership.Permission.PURCHASES_RECEIVE
        if action_name in {'order', 'cancel'}:
            permission = OrganizationMembership.Permission.PURCHASES_CREATE
        enforce_permission(
            request.user,
            purchase.organization,
            permission,
            f'You do not have permission to {action_name} purchases.',
        )
        if not user_can_access_branch(request.user, purchase.organization, purchase.branch):
            raise PermissionDenied('You do not have access to this branch.')
