from rest_framework.permissions import BasePermission
from django.db.models import Q

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


def user_has_permission(user, organization, permission):
    membership = get_active_membership(user, organization)
    return bool(membership and membership.has_permission(permission))


def require_permission(user, organization, permission):
    return user_has_permission(user, organization, permission)


def user_can_access_branch(user, organization, branch):
    membership = get_active_membership(user, organization)
    if not membership:
        return False
    if not branch:
        return True
    if branch.organization_id != organization.id:
        return False
    if membership.has_all_branch_access:
        return True
    return membership.branches.filter(id=branch.id).exists()


def filter_queryset_by_branch_access(queryset, user, organization_field='organization', branch_field='branch'):
    memberships = OrganizationMembership.objects.prefetch_related('branches').filter(
        user=user,
        is_active=True,
    )
    unrestricted_orgs = []
    restricted_pairs = []
    for membership in memberships:
        if membership.has_all_branch_access:
            unrestricted_orgs.append(membership.organization_id)
        else:
            for branch_id in membership.branches.values_list('id', flat=True):
                restricted_pairs.append((membership.organization_id, branch_id))

    access_filter = Q()
    if unrestricted_orgs:
        access_filter |= Q(**{f'{organization_field}_id__in': unrestricted_orgs})
    for organization_id, branch_id in restricted_pairs:
        access_filter |= Q(
            **{
                f'{organization_field}_id': organization_id,
                f'{branch_field}_id': branch_id,
            }
        )
    if not access_filter:
        return queryset.none()
    return queryset.filter(access_filter).distinct()


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
