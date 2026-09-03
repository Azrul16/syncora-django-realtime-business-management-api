from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.event_types import EventType
from apps.notifications.services.event_dispatcher import dispatch_event
from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import Expense, ExpenseCategory
from .serializers import ExpenseCategorySerializer, ExpenseSerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        return ExpenseCategory.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create expense categories.')
        serializer.save()


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'branch', 'category', 'status', 'expense_date']
    search_fields = ['title', 'description', 'reference', 'notes', 'expense_number']
    ordering_fields = ['expense_date', 'amount', 'created_at']

    def get_queryset(self):
        return Expense.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'category', 'created_by', 'approved_by').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        membership = get_active_membership(self.request.user, organization)
        if not membership:
            raise PermissionDenied('Only organization members can create expenses.')
        expense = serializer.save(created_by=self.request.user)
        dispatch_event(
            event=EventType.EXPENSE_CREATED,
            organization=expense.organization,
            actor=self.request.user,
            resource=expense,
            branch=expense.branch,
            data={'expense_id': expense.id, 'expense_number': expense.expense_number, 'status': expense.status},
            groups=[f'organization_{expense.organization_id}_finance'],
            notification_title='Expense awaiting approval',
            notification_message=f'{expense.expense_number} is waiting for approval.',
            activity_description=f'{expense.expense_number} was created.',
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        expense = self.get_object()
        self.ensure_can_approve_expense(request, expense, 'approve')

        try:
            expense.approve(request.user)
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.EXPENSE_APPROVED,
            organization=expense.organization,
            actor=request.user,
            resource=expense,
            branch=expense.branch,
            data={'expense_id': expense.id, 'expense_number': expense.expense_number, 'status': expense.status},
            groups=[f'organization_{expense.organization_id}_finance'],
            notification_title='Expense approved',
            notification_message=f'{expense.expense_number} was approved.',
            activity_description=f'{expense.expense_number} was approved.',
        )
        return Response(self.get_serializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        expense = self.get_object()
        self.ensure_can_approve_expense(request, expense, 'reject')

        try:
            expense.reject(request.user)
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.EXPENSE_REJECTED,
            organization=expense.organization,
            actor=request.user,
            resource=expense,
            branch=expense.branch,
            data={'expense_id': expense.id, 'expense_number': expense.expense_number, 'status': expense.status},
            groups=[f'organization_{expense.organization_id}_finance'],
            activity_description=f'{expense.expense_number} was rejected.',
        )
        return Response(self.get_serializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        expense = self.get_object()

        membership = get_active_membership(request.user, expense.organization)
        if not membership:
            raise PermissionDenied('Only organization members can cancel expenses.')
        if expense.created_by_id != request.user.id and not membership.is_manager:
            raise PermissionDenied('Only the creator or managers can cancel expenses.')

        try:
            expense.cancel()
        except DjangoValidationError as error:
            raise ValidationError({'status': error.messages}) from error

        dispatch_event(
            event=EventType.EXPENSE_CANCELLED,
            organization=expense.organization,
            actor=request.user,
            resource=expense,
            branch=expense.branch,
            data={'expense_id': expense.id, 'expense_number': expense.expense_number, 'status': expense.status},
            groups=[f'organization_{expense.organization_id}_finance'],
            activity_description=f'{expense.expense_number} was cancelled.',
        )
        return Response(self.get_serializer(expense).data, status=status.HTTP_200_OK)

    def ensure_can_approve_expense(self, request, expense, action_name):
        membership = get_active_membership(request.user, expense.organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied(
                f'Only organization owners, admins, or managers can {action_name} expenses.'
            )
