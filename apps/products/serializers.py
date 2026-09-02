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

    def validate(self, attrs):
        organization = attrs.get('organization') or getattr(self.instance, 'organization', None)
        category = attrs.get('category') or getattr(self.instance, 'category', None)
        if organization and category and category.organization_id != organization.id:
            raise serializers.ValidationError('Category must belong to the selected organization.')
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
