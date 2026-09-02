from rest_framework import serializers

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id',
            'organization',
            'name',
            'email',
            'phone',
            'address',
            'customer_code',
            'notes',
            'is_active',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {'customer_code': {'required': False, 'allow_blank': True}}
        validators = []

    def validate(self, attrs):
        organization = attrs.get('organization') or getattr(self.instance, 'organization', None)
        customer_code = attrs.get('customer_code', getattr(self.instance, 'customer_code', ''))
        if organization and customer_code:
            queryset = Customer.objects.filter(organization=organization, customer_code=customer_code)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {'customer_code': 'Customer code must be unique within the organization.'}
                )
        return attrs
