from rest_framework import serializers


class OrganizationDashboardSerializer(serializers.Serializer):
    organization = serializers.IntegerField()
    branches = serializers.IntegerField()
    products = serializers.IntegerField()
    customers = serializers.IntegerField()
    suppliers = serializers.IntegerField()
    inventory_units = serializers.DecimalField(max_digits=14, decimal_places=2)
    low_stock_items = serializers.IntegerField()
    purchase_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    sales_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses_total = serializers.DecimalField(max_digits=14, decimal_places=2)
