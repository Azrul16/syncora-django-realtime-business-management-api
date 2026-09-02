from rest_framework.permissions import BasePermission

from .models import OrganizationMembership


SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}


def get_active_membership(user, organization):
    if not user or not user.is_authenticated:
        return None
    return OrganizationMembership.objects.filter(
        user=user,
        organization=organization,
        is_active=True,
    ).first()


class IsOrganizationMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = getattr(obj, 'organization', obj)
        return get_active_membership(request.user, organization) is not None


class IsOrganizationAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = getattr(obj, 'organization', obj)
        membership = get_active_membership(request.user, organization)
        return bool(membership and membership.is_admin)


class IsOrganizationOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = getattr(obj, 'organization', obj)
        membership = get_active_membership(request.user, organization)
        return bool(membership and membership.is_owner)


class IsOrganizationMemberReadOnlyOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = getattr(obj, 'organization', obj)
        membership = get_active_membership(request.user, organization)

        if not membership:
            return False
        if request.method in SAFE_METHODS:
            return True
        return membership.is_admin


class IsOrganizationMemberReadOnlyOrManager(BasePermission):
    def has_object_permission(self, request, view, obj):
        organization = getattr(obj, 'organization', obj)
        membership = get_active_membership(request.user, organization)

        if not membership:
            return False
        if request.method in SAFE_METHODS:
            return True
        return membership.is_manager
