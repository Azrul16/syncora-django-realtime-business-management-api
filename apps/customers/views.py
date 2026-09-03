from decimal import Decimal

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.views import SoftDeleteViewSetMixin
from apps.finance.services.dashboard_analytics import DashboardAnalyticsService

from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.permissions import (
    IsOrganizationMember,
    enforce_permission,
)

from .models import Customer
from .serializers import CustomerSerializer


def serialize_money(value):
    if isinstance(value, Decimal):
        return f'{value:.2f}'
    if isinstance(value, dict):
        return {key: serialize_money(item) for key, item in value.items()}
    return value


class CustomerViewSet(SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_fields = ['organization', 'is_active']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        return Customer.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
            is_deleted=False,
        ).select_related('organization').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.SALES_CREATE,
            'You do not have permission to manage customers.',
        )
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        enforce_permission(
            self.request.user,
            serializer.instance.organization,
            OrganizationMembership.Permission.SALES_CREATE,
            'You do not have permission to manage customers.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        enforce_permission(
            self.request.user,
            instance.organization,
            OrganizationMembership.Permission.SALES_CREATE,
            'You do not have permission to manage customers.',
        )
        super().perform_destroy(instance)

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.request and self.request.method == 'POST':
            serializer.fields['organization'].queryset = Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
            )
        return serializer

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        customer = self.get_object()
        service = DashboardAnalyticsService(organization=customer.organization)
        return Response(serialize_money(service.get_customer_summary(customer)))
