from django.db import models
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.views import SoftDeleteViewSetMixin
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.permissions import (
    IsOrganizationMember,
    enforce_permission,
)

from .models import Branch
from .serializers import BranchSerializer


class BranchViewSet(SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_fields = ['organization', 'is_active', 'slug']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        queryset = Branch.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
            is_deleted=False,
        ).select_related('organization').distinct()
        memberships = self.request.user.organization_memberships.prefetch_related('branches').filter(is_active=True)
        restricted_branch_ids = []
        unrestricted_org_ids = []
        for membership in memberships:
            if membership.has_all_branch_access:
                unrestricted_org_ids.append(membership.organization_id)
            else:
                restricted_branch_ids.extend(membership.branches.values_list('id', flat=True))
        return queryset.filter(
            models.Q(organization_id__in=unrestricted_org_ids) | models.Q(id__in=restricted_branch_ids)
        ).distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.BRANCHES_MANAGE,
            'You do not have permission to manage branches.',
        )
        serializer.save()

    def perform_update(self, serializer):
        enforce_permission(
            self.request.user,
            serializer.instance.organization,
            OrganizationMembership.Permission.BRANCHES_MANAGE,
            'You do not have permission to manage branches.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        enforce_permission(
            self.request.user,
            instance.organization,
            OrganizationMembership.Permission.BRANCHES_MANAGE,
            'You do not have permission to manage branches.',
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
