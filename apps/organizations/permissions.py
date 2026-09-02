from rest_framework.permissions import BasePermission

from .models import OrganizationMembership


class IsOrganizationMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        organization = getattr(obj, 'organization', obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=organization,
            is_active=True,
        ).exists()


class IsOrganizationAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        organization = getattr(obj, 'organization', obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=organization,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
            is_active=True,
        ).exists()


class IsOrganizationOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        organization = getattr(obj, 'organization', obj)
        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        ).exists()
