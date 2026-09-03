from django.db import models
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.organizations.models import Organization
from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import Branch
from .serializers import BranchSerializer


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'is_active', 'slug']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        queryset = Branch.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
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
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create branches.')
        serializer.save()

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.request and self.request.method == 'POST':
            serializer.fields['organization'].queryset = Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
            )
        return serializer
