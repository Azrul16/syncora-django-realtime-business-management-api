from rest_framework import serializers

from apps.branches.models import Branch
from apps.products.models import Product, ProductVariant

from .models import InventoryStock, StockMovement
from .services import adjust_stock, increase_stock


class InventoryStockSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryStock
        fields = [
            'id',
            'organization',
            'branch',
            'product',
            'product_variant',
            'quantity',
            'reorder_level',
            'updated_by',
            'is_low_stock',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'updated_by', 'is_low_stock', 'updated_at']

    def validate(self, attrs):
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        product = attrs.get('product') or getattr(self.instance, 'product', None)
        product_variant = attrs.get('product_variant') or getattr(self.instance, 'product_variant', None)
        if product_variant:
            product = product_variant.product
            attrs['product'] = product
        if branch and product and branch.organization_id != product.organization_id:
            raise serializers.ValidationError('Inventory item must belong to the branch organization.')
        return attrs

    def create(self, validated_data):
        branch = validated_data['branch']
        quantity = validated_data.pop('quantity', 0)
        reorder_level = validated_data.pop('reorder_level', 0)

        if quantity:
            stock, _ = increase_stock(
                branch=branch,
                product_variant=validated_data.get('product_variant'),
                product=validated_data.get('product'),
                quantity=quantity,
                movement_type=StockMovement.MovementType.OPENING_STOCK,
                reference='opening-stock',
                note='Opening stock created through REST API.',
                user=self.context['request'].user,
            )
            stock.reorder_level = reorder_level
            stock.save(update_fields=['reorder_level', 'updated_at'])
            return stock

        validated_data['organization'] = branch.organization
        validated_data['quantity'] = quantity
        validated_data['reorder_level'] = reorder_level
        validated_data['updated_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        quantity = validated_data.pop('quantity', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if quantity is not None:
            stock, _ = adjust_stock(
                stock=instance,
                new_quantity=quantity,
                reference='inventory-api',
                note='Inventory quantity adjusted through REST API.',
                user=self.context['request'].user,
            )
            return stock
        instance.save()
        return instance

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
        self.fields['product_variant'].queryset = ProductVariant.objects.filter(
            product__organization_id__in=organizations
        )


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            'id',
            'organization',
            'branch',
            'product',
            'product_variant',
            'movement_type',
            'quantity',
            'previous_quantity',
            'new_quantity',
            'reference',
            'note',
            'created_by',
            'created_at',
        ]
        read_only_fields = fields
