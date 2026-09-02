from rest_framework import serializers

from .models import Organization, OrganizationMembership


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'email', 'phone', 'address', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ['id', 'user', 'user_email', 'organization', 'role', 'is_active', 'joined_at']
        read_only_fields = ['id', 'user', 'user_email', 'organization', 'joined_at']


class OrganizationMembershipCreateSerializer(serializers.Serializer):
    user_email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.EMPLOYEE,
    )


class OrganizationMembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=OrganizationMembership.Role.choices,
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
