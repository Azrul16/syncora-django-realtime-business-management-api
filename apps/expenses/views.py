from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.views import SoftDeleteViewSetMixin
from apps.notifications.event_types import EventType
from apps.notifications.services.event_dispatcher import dispatch_event
from apps.organizations.models import OrganizationMembership
from apps.organizations.permissions import (
    IsOrganizationMember,
    enforce_permission,
    filter_queryset_by_branch_access,
    get_active_membership,
    user_can_access_branch,
)

from .models import Expense, ExpenseCategory
from .filters import ExpenseFilter
from .serializers import ExpenseCategorySerializer, ExpenseSerializer


class ExpenseCategoryViewSet(SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_fields = ['organization', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        return ExpenseCategory.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
            is_deleted=False,
        ).select_related('organization').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.EXPENSES_APPROVE,
            'You do not have permission to manage expense categories.',
        )
        serializer.save()

    def perform_update(self, serializer):
        enforce_permission(
            self.request.user,
            serializer.instance.organization,
            OrganizationMembership.Permission.EXPENSES_APPROVE,
            'You do not have permission to manage expense categories.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        enforce_permission(
            self.request.user,
            instance.organization,
            OrganizationMembership.Permission.EXPENSES_APPROVE,
            'You do not have permission to manage expense categories.',
        )
        super().perform_destroy(instance)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_class = ExpenseFilter
    search_fields = ['title', 'description', 'reference', 'notes', 'expense_number']
    ordering_fields = ['expense_date', 'amount', 'created_at']

    def get_queryset(self):
        queryset = Expense.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'branch', 'category', 'created_by', 'approved_by').distinct()
        return filter_queryset_by_branch_access(queryset, self.request.user)

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.EXPENSES_CREATE,
            'You do not have permission to create expenses.',
        )
        if not user_can_access_branch(self.request.user, organization, serializer.validated_data.get('branch')):
            raise PermissionDenied('You do not have access to this branch.')
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

    def perform_update(self, serializer):
        expense = serializer.instance
        membership = get_active_membership(self.request.user, expense.organization)
        if not membership:
            raise PermissionDenied('Only organization members can update expenses.')
        if expense.created_by_id != self.request.user.id and not membership.has_permission(
            OrganizationMembership.Permission.EXPENSES_APPROVE
        ):
            raise PermissionDenied('Only the creator or expense approvers can update expenses.')
        if not user_can_access_branch(self.request.user, expense.organization, expense.branch):
            raise PermissionDenied('You do not have access to this branch.')
        serializer.save()

    def perform_destroy(self, instance):
        membership = get_active_membership(self.request.user, instance.organization)
        if not membership:
            raise PermissionDenied('Only organization members can delete expenses.')
        if instance.created_by_id != self.request.user.id and not membership.has_permission(
            OrganizationMembership.Permission.EXPENSES_APPROVE
        ):
            raise PermissionDenied('Only the creator or expense approvers can delete expenses.')
        if not user_can_access_branch(self.request.user, instance.organization, instance.branch):
            raise PermissionDenied('You do not have access to this branch.')
        super().perform_destroy(instance)

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
        if expense.created_by_id != request.user.id and not membership.has_permission(
            OrganizationMembership.Permission.EXPENSES_APPROVE
        ):
            raise PermissionDenied('Only the creator or managers can cancel expenses.')
        if not user_can_access_branch(request.user, expense.organization, expense.branch):
            raise PermissionDenied('You do not have access to this branch.')

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
        enforce_permission(
            request.user,
            expense.organization,
            OrganizationMembership.Permission.EXPENSES_APPROVE,
            f'You do not have permission to {action_name} expenses.',
        )
        if not user_can_access_branch(request.user, expense.organization, expense.branch):
            raise PermissionDenied('You do not have access to this branch.')
