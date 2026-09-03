from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.event_types import EventType
from apps.notifications.services.event_dispatcher import dispatch_event
from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    filter_queryset_by_branch_access,
    get_active_membership,
    user_can_access_branch,
)

from .models import Purchase
from .serializers import PurchaseSerializer


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'supplier', 'status']
    search_fields = ['reference', 'purchase_number', 'supplier__name', 'branch__name']
    ordering_fields = ['order_date', 'created_at', 'updated_at', 'received_at']

    def get_queryset(self):
        queryset = Purchase.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'supplier').prefetch_related('items__product').distinct()
        queryset = filter_queryset_by_branch_access(queryset, self.request.user)
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
        return queryset

    def perform_create(self, serializer):
        organization = serializer.validated_data['branch'].organization
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create purchases.')
        if not user_can_access_branch(self.request.user, organization, serializer.validated_data['branch']):
            raise PermissionDenied('You do not have access to this branch.')
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
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
        membership = get_active_membership(request.user, purchase.organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied(
                f'Only organization owners, admins, or managers can {action_name} purchases.'
            )
        if not user_can_access_branch(request.user, purchase.organization, purchase.branch):
            raise PermissionDenied('You do not have access to this branch.')
