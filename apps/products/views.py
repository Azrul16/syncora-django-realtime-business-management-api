from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.views import SoftDeleteViewSetMixin
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.permissions import (
    IsOrganizationMember,
    enforce_permission,
)

from .models import Product, ProductCategory, ProductVariant
from .serializers import ProductCategorySerializer, ProductSerializer, ProductVariantSerializer


class ProductCategoryViewSet(SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_fields = ['organization', 'is_active', 'slug']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        return ProductCategory.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
            is_deleted=False,
        ).select_related('organization').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        serializer.save()

    def perform_update(self, serializer):
        enforce_permission(
            self.request.user,
            serializer.instance.organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        enforce_permission(
            self.request.user,
            instance.organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        super().perform_destroy(instance)


class ProductViewSet(SoftDeleteViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_fields = ['organization', 'is_active', 'sku', 'slug']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'sku', 'created_at', 'updated_at']

    def get_queryset(self):
        return Product.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
            is_deleted=False,
        ).select_related('organization').distinct()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        enforce_permission(
            self.request.user,
            organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        enforce_permission(
            self.request.user,
            serializer.instance.organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        enforce_permission(
            self.request.user,
            instance.organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
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


class ProductVariantViewSet(viewsets.ModelViewSet):
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
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
        enforce_permission(
            self.request.user,
            product.organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        serializer.save()

    def perform_update(self, serializer):
        enforce_permission(
            self.request.user,
            serializer.instance.product.organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        serializer.save()

    def perform_destroy(self, instance):
        enforce_permission(
            self.request.user,
            instance.product.organization,
            OrganizationMembership.Permission.PRODUCTS_MANAGE,
            'You do not have permission to manage products.',
        )
        super().perform_destroy(instance)
