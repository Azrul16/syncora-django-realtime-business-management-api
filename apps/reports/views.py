from decimal import Decimal

from django.db.models import DecimalField, F, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.expenses.models import Expense
from apps.inventory.models import InventoryStock
from apps.organizations.models import Organization
from apps.organizations.permissions import get_active_membership
from apps.purchases.models import Purchase, PurchaseItem
from apps.sales.models import Sale

from .serializers import OrganizationDashboardSerializer


def decimal_sum(value):
    return value or Decimal('0')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organization_dashboard(request, organization_id):
    organization = Organization.objects.filter(id=organization_id).first()
    if not organization or not get_active_membership(request.user, organization):
        raise NotFound('Organization was not found.')

    inventory = InventoryStock.objects.filter(organization=organization)
    low_stock_items = inventory.filter(quantity__lte=F('reorder_level')).count()
    purchase_total = PurchaseItem.objects.filter(
        purchase__organization=organization,
        purchase__status=Purchase.Status.RECEIVED,
    ).aggregate(
        total=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField(max_digits=14, decimal_places=2))
    )['total']
    sales_total = Sale.objects.filter(
        organization=organization,
        status=Sale.Status.COMPLETED,
    ).aggregate(total=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)))['total']

    data = {
        'organization': organization.id,
        'branches': organization.branches.filter(is_active=True).count(),
        'products': organization.products.filter(is_active=True).count(),
        'customers': organization.customers.filter(is_active=True).count(),
        'suppliers': organization.suppliers.filter(is_active=True).count(),
        'inventory_units': decimal_sum(inventory.aggregate(total=Sum('quantity'))['total']),
        'low_stock_items': low_stock_items,
        'purchase_total': decimal_sum(purchase_total),
        'sales_total': decimal_sum(sales_total),
        'expenses_total': decimal_sum(
            Expense.objects.filter(organization=organization).aggregate(total=Sum('amount'))['total']
        ),
    }
    serializer = OrganizationDashboardSerializer(data)
    return Response(serializer.data)
