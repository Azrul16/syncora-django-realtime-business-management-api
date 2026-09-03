from rest_framework import serializers

from apps.organizations.models import Organization

from .models import Product, ProductCategory, ProductVariant


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = [
            'id',
            'organization',
            'name',
            'slug',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            self.fields['organization'].queryset = Organization.objects.filter(
                memberships__user=request.user,
                memberships__is_active=True,
            )


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'organization',
            'category',
            'name',
            'slug',
            'sku',
            'description',
            'brand',
            'unit',
            'cost_price',
            'selling_price',
            'is_active',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_by', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            organization_ids = request.user.organization_memberships.filter(
                is_active=True,
            ).values_list('organization_id', flat=True)
            self.fields['organization'].queryset = Organization.objects.filter(id__in=organization_ids)
            self.fields['category'].queryset = ProductCategory.objects.filter(organization_id__in=organization_ids)

    def validate(self, attrs):
        organization = attrs.get('organization') or getattr(self.instance, 'organization', None)
        category = attrs.get('category') or getattr(self.instance, 'category', None)
        if organization and category and category.organization_id != organization.id:
            raise serializers.ValidationError('Category must belong to the selected organization.')
        for field in ['cost_price', 'selling_price']:
            if attrs.get(field, 0) < 0:
                raise serializers.ValidationError({field: f'{field} cannot be negative.'})
        return attrs


class ProductVariantSerializer(serializers.ModelSerializer):
    organization = serializers.IntegerField(source='product.organization_id', read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id',
            'organization',
            'product',
            'sku',
            'name',
            'cost_price',
            'selling_price',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']

    def validate(self, attrs):
        for field in ['cost_price', 'selling_price']:
            if attrs.get(field, 0) < 0:
                raise serializers.ValidationError({field: f'{field} cannot be negative.'})
        return attrs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            organization_ids = request.user.organization_memberships.filter(
                is_active=True,
            ).values_list('organization_id', flat=True)
            self.fields['product'].queryset = Product.objects.filter(organization_id__in=organization_ids)
