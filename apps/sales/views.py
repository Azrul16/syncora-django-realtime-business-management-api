from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.event_types import EventType
from apps.notifications.services.event_dispatcher import dispatch_event
from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import Payment, Sale
from .serializers import PaymentSerializer, SaleSerializer


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'customer', 'status']
    search_fields = ['reference', 'sale_number', 'customer__name', 'branch__name']
    ordering_fields = ['sale_date', 'created_at', 'updated_at', 'completed_at']

    def get_queryset(self):
        queryset = Sale.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'customer').prefetch_related(
            'items__product',
            'payments',
        ).distinct()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        payment_status = self.request.query_params.get('payment_status')
        if date_from:
            queryset = queryset.filter(sale_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(sale_date__lte=date_to)
        if payment_status:
            queryset = queryset.annotate(
                paid_total=Coalesce(
                    Sum('payments__amount'),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
            if payment_status == Sale.PaymentStatus.UNPAID:
                queryset = queryset.filter(paid_total__lte=0)
            elif payment_status == Sale.PaymentStatus.PARTIALLY_PAID:
                queryset = queryset.filter(paid_total__gt=0, paid_total__lt=F('grand_total'))
            elif payment_status == Sale.PaymentStatus.PAID:
                queryset = queryset.filter(paid_total__gte=F('grand_total'))
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        organization = serializer.validated_data['branch'].organization
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create sales.')
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.status in {Sale.Status.COMPLETED, Sale.Status.CANCELLED}:
            raise ValidationError({'status': 'Completed or cancelled sales cannot be edited.'})
        serializer.save()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        sale = self.get_object()
        self.ensure_can_manage_sale(request, sale, 'confirm')

        try:
            sale.confirm()
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.SALE_CONFIRMED,
            organization=sale.organization,
            actor=request.user,
            resource=sale,
            branch=sale.branch,
            data={'sale_id': sale.id, 'sale_number': sale.sale_number, 'status': sale.status},
            groups=[f'organization_{sale.organization_id}_sales'],
            activity_description=f'{sale.sale_number} was confirmed.',
        )
        return Response(self.get_serializer(sale).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        sale = self.get_object()
        self.ensure_can_manage_sale(request, sale, 'complete')

        serializer = self.get_serializer()
        serializer.complete(sale)
        dispatch_event(
            event=EventType.SALE_COMPLETED,
            organization=sale.organization,
            actor=request.user,
            resource=sale,
            branch=sale.branch,
            data={
                'sale_id': sale.id,
                'sale_number': sale.sale_number,
                'status': sale.status,
                'total': str(sale.grand_total),
                'payment_status': sale.payment_status,
            },
            groups=[
                f'organization_{sale.organization_id}_sales',
                f'organization_{sale.organization_id}_finance',
            ],
            notification_title='Sale completed',
            notification_message=f'{sale.sale_number} was completed for {sale.grand_total}.',
            activity_description=f'{sale.sale_number} was completed.',
        )
        return Response(self.get_serializer(sale).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        sale = self.get_object()
        self.ensure_can_manage_sale(request, sale, 'cancel')

        try:
            sale.cancel()
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.SALE_CANCELLED,
            organization=sale.organization,
            actor=request.user,
            resource=sale,
            branch=sale.branch,
            data={'sale_id': sale.id, 'sale_number': sale.sale_number, 'status': sale.status},
            groups=[f'organization_{sale.organization_id}_sales'],
            activity_description=f'{sale.sale_number} was cancelled.',
        )
        return Response(self.get_serializer(sale).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'])
    def payments(self, request, pk=None):
        sale = self.get_object()
        if request.method == 'GET':
            payments = sale.payments.select_related('sale', 'organization', 'received_by')
            return Response(PaymentSerializer(payments, many=True).data, status=status.HTTP_200_OK)

        self.ensure_can_manage_sale(request, sale, 'receive payments for')
        data = request.data.copy()
        data['sale'] = sale.id
        serializer = PaymentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = serializer.save(received_by=request.user)
        except DjangoValidationError as error:
            raise ValidationError({'payment': error.messages}) from error

        dispatch_event(
            event=EventType.PAYMENT_CREATED,
            organization=sale.organization,
            actor=request.user,
            resource=payment,
            branch=sale.branch,
            data={
                'payment_id': payment.id,
                'sale_id': sale.id,
                'sale_number': sale.sale_number,
                'amount': str(payment.amount),
                'payment_status': sale.payment_status,
                'paid_amount': str(sale.paid_amount),
                'due_amount': str(sale.due_amount),
            },
            groups=[
                f'organization_{sale.organization_id}_payments',
                f'organization_{sale.organization_id}_finance',
            ],
            notification_title='Payment received',
            notification_message=f'Payment received for {sale.sale_number}: {payment.amount}.',
            activity_description=f'Payment received for {sale.sale_number}.',
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    def ensure_can_manage_sale(self, request, sale, action_name):
        membership = get_active_membership(request.user, sale.organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied(
                f'Only organization owners, admins, or managers can {action_name} sales.'
            )
