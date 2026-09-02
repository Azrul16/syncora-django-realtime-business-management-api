from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.organizations.models import Organization
from apps.organizations.permissions import (
    IsOrganizationMemberReadOnlyOrManager,
    get_active_membership,
)

from .models import Product, ProductCategory, ProductVariant
from .serializers import ProductCategorySerializer, ProductSerializer, ProductVariantSerializer


class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'is_active', 'slug']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        return ProductCategory.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create categories.')
        serializer.save()


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['organization', 'is_active', 'sku', 'slug']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'sku', 'created_at', 'updated_at']

    def get_queryset(self):
        return Product.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        membership = get_active_membership(self.request.user, organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create products.')
        serializer.save(created_by=self.request.user)

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.request and self.request.method == 'POST':
            serializer.fields['organization'].queryset = Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
            )
        return serializer


class ProductVariantViewSet(viewsets.ModelViewSet):
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMemberReadOnlyOrManager]
    filterset_fields = ['product', 'is_active', 'sku']
    search_fields = ['name', 'sku', 'product__name']
    ordering_fields = ['name', 'sku', 'created_at', 'updated_at']

    def get_queryset(self):
        return ProductVariant.objects.filter(
            product__organization__memberships__user=self.request.user,
            product__organization__memberships__is_active=True,
        ).select_related('product', 'product__organization').distinct()

    def perform_create(self, serializer):
        product = serializer.validated_data['product']
        membership = get_active_membership(self.request.user, product.organization)
        if not membership or not membership.is_manager:
            raise PermissionDenied('Only organization owners, admins, or managers can create product variants.')
        serializer.save()
