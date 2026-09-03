from rest_framework import serializers

from apps.branches.models import Branch
from apps.organizations.models import Organization

from .models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = [
            'id',
            'organization',
            'name',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            'id',
            'organization',
            'branch',
            'category',
            'legacy_category',
            'expense_number',
            'title',
            'amount',
            'expense_date',
            'status',
            'description',
            'reference',
            'notes',
            'created_by',
            'approved_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'legacy_category',
            'expense_number',
            'status',
            'created_by',
            'approved_by',
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
        self.fields['organization'].queryset = Organization.objects.filter(id__in=organizations)
        self.fields['branch'].queryset = Branch.objects.filter(organization_id__in=organizations)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(organization_id__in=organizations)

    def validate(self, attrs):
        organization = attrs.get('organization') or getattr(self.instance, 'organization', None)
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        category = attrs.get('category') or getattr(self.instance, 'category', None)
        if organization and branch and branch.organization_id != organization.id:
            raise serializers.ValidationError('Branch must belong to the selected organization.')
        if organization and category and category.organization_id != organization.id:
            raise serializers.ValidationError('Category must belong to the selected organization.')
        if attrs.get('amount', 0) <= 0:
            raise serializers.ValidationError({'amount': 'Amount must be greater than zero.'})
        return attrs
