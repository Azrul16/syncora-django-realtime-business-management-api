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
            'title',
            'amount',
            'expense_date',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

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

    def validate(self, attrs):
        organization = attrs.get('organization') or getattr(self.instance, 'organization', None)
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        if organization and branch and branch.organization_id != organization.id:
            raise serializers.ValidationError('Branch must belong to the selected organization.')
        return attrs
