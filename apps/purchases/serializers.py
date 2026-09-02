from rest_framework import serializers

from apps.branches.models import Branch
from apps.products.models import Product, ProductVariant
from apps.suppliers.models import Supplier

from .models import Purchase, PurchaseItem


class PurchaseItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ['id', 'product', 'product_variant', 'quantity', 'unit_cost', 'discount', 'tax', 'line_total']
        read_only_fields = ['id', 'line_total']
        extra_kwargs = {'product': {'required': False}}


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = [
            'id',
            'organization',
            'branch',
            'supplier',
            'reference',
            'purchase_number',
            'status',
            'order_date',
            'expected_date',
            'notes',
            'discount_amount',
            'tax_amount',
            'shipping_cost',
            'subtotal',
            'grand_total',
            'created_by',
            'items',
            'total_amount',
            'received_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization',
            'purchase_number',
            'status',
            'subtotal',
            'grand_total',
            'created_by',
            'total_amount',
            'received_at',
            'created_at',
            'updated_at',
        ]

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
        self.fields['supplier'].queryset = Supplier.objects.filter(organization_id__in=organizations)
        self.fields['items'].child.fields['product'].queryset = Product.objects.filter(
            organization_id__in=organizations
        )
        self.fields['items'].child.fields['product_variant'].queryset = ProductVariant.objects.filter(
            product__organization_id__in=organizations
        )

    def validate(self, attrs):
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        supplier = attrs.get('supplier') or getattr(self.instance, 'supplier', None)
        items = attrs.get('items', [])

        if branch and supplier and branch.organization_id != supplier.organization_id:
            raise serializers.ValidationError('Branch and supplier must belong to the same organization.')

        for item in items:
            product = item.get('product')
            product_variant = item.get('product_variant')
            if product_variant:
                if product and product_variant.product_id != product.id:
                    raise serializers.ValidationError('Product variant must belong to its line item product.')
                item['product'] = product_variant.product
                product = product_variant.product
            if not product:
                raise serializers.ValidationError('Each purchase item requires a product or product variant.')
            if branch and product.organization_id != branch.organization_id:
                raise serializers.ValidationError('All products must belong to the branch organization.')

        return attrs

    def create(self, validated_data):
        items = validated_data.pop('items')
        branch = validated_data['branch']
        purchase = Purchase.objects.create(
            organization=branch.organization,
            **validated_data,
        )
        PurchaseItem.objects.bulk_create(
            PurchaseItem(purchase=purchase, **item)
            for item in items
        )
        purchase.recalculate_totals()
        return purchase
