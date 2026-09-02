from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.products.models import Product, ProductVariant

from .models import Payment, Sale, SaleItem


class SaleItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = SaleItem
        fields = ['id', 'product', 'product_variant', 'quantity', 'unit_cost', 'unit_price', 'discount', 'tax', 'line_total']
        read_only_fields = ['id', 'unit_cost', 'line_total']
        extra_kwargs = {'product': {'required': False}}


class PaymentSerializer(serializers.ModelSerializer):
    payment_status = serializers.CharField(source='sale.payment_status', read_only=True)
    paid_amount = serializers.DecimalField(source='sale.paid_amount', max_digits=12, decimal_places=2, read_only=True)
    due_amount = serializers.DecimalField(source='sale.due_amount', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'sale',
            'organization',
            'amount',
            'payment_method',
            'reference_number',
            'paid_at',
            'received_by',
            'notes',
            'payment_status',
            'paid_amount',
            'due_amount',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'organization',
            'received_by',
            'payment_status',
            'paid_amount',
            'due_amount',
            'created_at',
        ]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    due_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    payment_status = serializers.CharField(read_only=True)

    class Meta:
        model = Sale
        fields = [
            'id',
            'organization',
            'branch',
            'customer',
            'reference',
            'sale_number',
            'status',
            'sale_date',
            'notes',
            'discount_amount',
            'tax_amount',
            'subtotal',
            'grand_total',
            'created_by',
            'items',
            'total_amount',
            'paid_amount',
            'due_amount',
            'payment_status',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization',
            'sale_number',
            'status',
            'subtotal',
            'grand_total',
            'created_by',
            'total_amount',
            'paid_amount',
            'due_amount',
            'payment_status',
            'completed_at',
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
            item['unit_cost'] = product_variant.cost_price if product_variant else product.cost_price

        return attrs

    def create(self, validated_data):
        items = validated_data.pop('items')
        branch = validated_data['branch']
        sale = Sale.objects.create(
            organization=branch.organization,
            **validated_data,
        )
        SaleItem.objects.bulk_create(SaleItem(sale=sale, **item) for item in items)
        sale.recalculate_totals()
        return sale

    def update(self, instance, validated_data):
        items = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items is not None:
            instance.items.all().delete()
            SaleItem.objects.bulk_create(SaleItem(sale=instance, **item) for item in items)

        instance.recalculate_totals()
        return instance

    def complete(self, sale):
        try:
            sale.complete()
        except DjangoValidationError as error:
            raise serializers.ValidationError({'stock': error.messages}) from error
        return sale
