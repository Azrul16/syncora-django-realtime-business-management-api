from rest_framework import serializers

from apps.branches.models import Branch
from apps.products.models import Product
from apps.suppliers.models import Supplier

from .models import Purchase, PurchaseItem


class PurchaseItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ['id', 'product', 'quantity', 'unit_cost', 'line_total']
        read_only_fields = ['id', 'line_total']


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
            'status',
            'notes',
            'items',
            'total_amount',
            'received_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'status', 'total_amount', 'received_at', 'created_at', 'updated_at']

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

    def validate(self, attrs):
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        supplier = attrs.get('supplier') or getattr(self.instance, 'supplier', None)
        items = attrs.get('items', [])

        if branch and supplier and branch.organization_id != supplier.organization_id:
            raise serializers.ValidationError('Branch and supplier must belong to the same organization.')

        for item in items:
            product = item['product']
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
        return purchase
