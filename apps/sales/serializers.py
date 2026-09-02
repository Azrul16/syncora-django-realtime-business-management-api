from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.products.models import Product, ProductVariant

from .models import Sale, SaleItem


class SaleItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = SaleItem
        fields = ['id', 'product', 'product_variant', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['id', 'line_total']
        extra_kwargs = {'product': {'required': False}}


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Sale
        fields = [
            'id',
            'organization',
            'branch',
            'customer',
            'reference',
            'status',
            'notes',
            'items',
            'total_amount',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'status', 'total_amount', 'completed_at', 'created_at', 'updated_at']

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
        self.fields['customer'].queryset = Customer.objects.filter(organization_id__in=organizations)
        self.fields['items'].child.fields['product'].queryset = Product.objects.filter(
            organization_id__in=organizations
        )
        self.fields['items'].child.fields['product_variant'].queryset = ProductVariant.objects.filter(
            product__organization_id__in=organizations
        )

    def validate(self, attrs):
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        customer = attrs.get('customer') or getattr(self.instance, 'customer', None)
        items = attrs.get('items', [])

        if branch and customer and branch.organization_id != customer.organization_id:
            raise serializers.ValidationError('Branch and customer must belong to the same organization.')

        for item in items:
            product = item.get('product')
            product_variant = item.get('product_variant')
            if product_variant:
                if product and product_variant.product_id != product.id:
                    raise serializers.ValidationError('Product variant must belong to its line item product.')
                item['product'] = product_variant.product
                product = product_variant.product
            if not product:
                raise serializers.ValidationError('Each sale item requires a product or product variant.')
            if branch and product.organization_id != branch.organization_id:
                raise serializers.ValidationError('All products must belong to the branch organization.')

        return attrs

    def create(self, validated_data):
        items = validated_data.pop('items')
        branch = validated_data['branch']
        sale = Sale.objects.create(
            organization=branch.organization,
            **validated_data,
        )
        SaleItem.objects.bulk_create(SaleItem(sale=sale, **item) for item in items)
        return sale

    def complete(self, sale):
        try:
            sale.complete()
        except DjangoValidationError as error:
            raise serializers.ValidationError({'stock': error.messages}) from error
        return sale
