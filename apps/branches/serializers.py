from rest_framework import serializers

from .models import Branch


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            'id',
            'organization',
            'name',
            'code',
            'slug',
            'email',
            'phone',
            'address',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
