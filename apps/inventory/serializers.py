from rest_framework import serializers

from apps.branches.models import Branch
from apps.products.models import Product

from .models import InventoryStock


class InventoryStockSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryStock
        fields = [
            'id',
            'organization',
            'branch',
            'product',
            'quantity',
            'reorder_level',
            'is_low_stock',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'is_low_stock', 'updated_at']

    def validate(self, attrs):
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        product = attrs.get('product') or getattr(self.instance, 'product', None)
        if branch and product and branch.organization_id != product.organization_id:
            raise serializers.ValidationError('Branch and product must belong to the same organization.')
        return attrs

    def create(self, validated_data):
        branch = validated_data['branch']
        validated_data['organization'] = branch.organization
        return super().create(validated_data)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request:
            return

        organizations = {
            membership.organization_id
            for membership in request.user.organization_memberships.filter(is_active=True)
        }
        self.fields['branch'].queryset = Branch.objects.filter(organization_id__in=organizations)
        self.fields['product'].queryset = Product.objects.filter(organization_id__in=organizations)
