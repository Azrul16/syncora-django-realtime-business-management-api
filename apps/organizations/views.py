from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

from apps.notifications.event_types import EventType, build_realtime_event
from apps.notifications.services.audit import record_audit_event

from apps.branches.models import Branch

from .models import Organization, OrganizationMembership
from .permissions import enforce_permission, get_active_membership
from .permissions import IsOrganizationMemberReadOnlyOrAdmin
from .serializers import (
    OrganizationMembershipCreateSerializer,
    OrganizationMembershipSerializer,
    OrganizationMembershipUpdateSerializer,
    OrganizationSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrAdmin]
    filterset_fields = ['name', 'slug']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        organization = serializer.save()
        OrganizationMembership.objects.create(
            user=self.request.user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )

    def perform_update(self, serializer):
        organization = serializer.save()
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'organization_{organization.id}',
                build_realtime_event(
                    EventType.ORGANIZATION_UPDATED,
                    organization.id,
                    OrganizationSerializer(organization).data,
                ),
            )

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        organization = self.get_object()

        if request.method == 'POST':
            serializer = OrganizationMembershipCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            membership = self.add_member(organization, serializer.validated_data)
            return Response(
                OrganizationMembershipSerializer(membership).data,
                status=status.HTTP_201_CREATED,
            )

        memberships = organization.memberships.select_related('user').filter(is_active=True)
        serializer = OrganizationMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @extend_schema(
        parameters=[OpenApiParameter('membership_id', OpenApiTypes.INT, OpenApiParameter.PATH)],
        request=OrganizationMembershipUpdateSerializer,
        responses=OrganizationMembershipSerializer,
    )
    @action(detail=True, methods=['patch', 'delete'], url_path='members/(?P<membership_id>[^/.]+)')
    def member(self, request, pk=None, membership_id=None):
        organization = self.get_object()
        membership = organization.memberships.select_related('user').filter(id=membership_id).first()

        if not membership:
            raise NotFound('Membership was not found for this organization.')

        actor_membership = get_active_membership(request.user, organization)
        self.ensure_can_manage_membership(actor_membership, membership)

        if request.method == 'DELETE':
            self.ensure_not_last_owner(membership)
            membership.is_active = False
            membership.save(update_fields=['is_active'])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = OrganizationMembershipUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_membership = self.update_member(actor_membership, membership, serializer.validated_data)
        return Response(OrganizationMembershipSerializer(updated_membership).data)

    def add_member(self, organization, data):
        actor_membership = get_active_membership(self.request.user, organization)
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.USERS_MANAGE,
            'You do not have permission to manage organization members.',
        )
        role = data['role']

        if role == OrganizationMembership.Role.OWNER and not actor_membership.is_owner:
            raise PermissionDenied('Only owners can add another owner.')

        user = get_user_model().objects.filter(email__iexact=data['user_email']).first()
        if not user:
            raise ValidationError({'user_email': 'No user exists with this email address.'})

        membership, created = OrganizationMembership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={'role': role},
        )

        if not created and membership.is_active:
            raise ValidationError({'user_email': 'User is already an active member.'})

        if not created:
            old_role = membership.role
            membership.role = role
            membership.is_active = True
            membership.save(update_fields=['role', 'is_active'])
            if old_role != role:
                record_audit_event(
                    action='role.changed',
                    request=self.request,
                    organization=organization,
                    target=membership.user,
                    metadata={'old_role': old_role, 'new_role': role},
                )

        self.update_branch_assignments(membership, data.get('branches'))
        return membership

    def update_member(self, actor_membership, membership, data):
        new_role = data.get('role', membership.role)
        new_is_active = data.get('is_active', membership.is_active)

        if new_role == OrganizationMembership.Role.OWNER and not actor_membership.is_owner:
            raise PermissionDenied('Only owners can assign the owner role.')
        if membership.is_owner and not actor_membership.is_owner:
            raise PermissionDenied('Only owners can change an owner membership.')
        if membership.is_owner and (new_role != membership.role or not new_is_active):
            self.ensure_not_last_owner(membership)

        old_role = membership.role
        old_is_active = membership.is_active
        membership.role = new_role
        membership.is_active = new_is_active
        membership.save(update_fields=['role', 'is_active'])
        if old_role != new_role:
            record_audit_event(
                action='role.changed',
                request=self.request,
                organization=membership.organization,
                target=membership.user,
                metadata={'old_role': old_role, 'new_role': new_role},
            )
        if old_is_active != new_is_active:
            record_audit_event(
                action='membership.status.changed',
                request=self.request,
                organization=membership.organization,
                target=membership.user,
                metadata={'old_is_active': old_is_active, 'new_is_active': new_is_active},
            )
        self.update_branch_assignments(membership, data.get('branches'))
        return membership

    def update_branch_assignments(self, membership, branch_ids):
        if branch_ids is None:
            return
        old_branch_ids = sorted(membership.branches.values_list('id', flat=True))
        branches = Branch.objects.filter(
            organization=membership.organization,
            id__in=branch_ids,
        )
        if branches.count() != len(set(branch_ids)):
            raise ValidationError({'branches': 'All assigned branches must belong to this organization.'})
        membership.branches.set(branches)
        new_branch_ids = sorted(branches.values_list('id', flat=True))
        if old_branch_ids != new_branch_ids:
            record_audit_event(
                action='branch.access.changed',
                request=self.request,
                organization=membership.organization,
                target=membership.user,
                metadata={'old_branches': old_branch_ids, 'new_branches': new_branch_ids},
            )

    def ensure_can_manage_membership(self, actor_membership, membership):
        if not actor_membership or not actor_membership.has_permission(OrganizationMembership.Permission.USERS_MANAGE):
            raise PermissionDenied('You do not have permission to manage organization members.')
        if actor_membership.id == membership.id:
            raise PermissionDenied('You cannot manage your own membership through this endpoint.')

    def ensure_not_last_owner(self, membership):
        if not membership.is_owner or not membership.is_active:
            return

        active_owner_count = OrganizationMembership.objects.filter(
            organization=membership.organization,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        ).count()
        if active_owner_count <= 1:
            raise ValidationError({'role': 'An organization must keep at least one active owner.'})
