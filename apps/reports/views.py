from decimal import Decimal

from django.db.models import DecimalField, F, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.expenses.models import Expense
from apps.inventory.models import InventoryStock
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.permissions import enforce_permission, filter_queryset_by_branch_access, get_active_membership
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
    enforce_permission(
        request.user,
        organization,
        OrganizationMembership.Permission.REPORTS_VIEW,
        'You do not have permission to view reports.',
    )

    inventory = filter_queryset_by_branch_access(
        InventoryStock.objects.filter(organization=organization),
        request.user,
    )
    low_stock_items = inventory.filter(quantity__lte=F('reorder_level')).count()
    purchases = filter_queryset_by_branch_access(
        Purchase.objects.filter(
            organization=organization,
            status=Purchase.Status.RECEIVED,
        ),
        request.user,
    )
    sales = filter_queryset_by_branch_access(
        Sale.objects.filter(
            organization=organization,
            status=Sale.Status.COMPLETED,
        ),
        request.user,
    )
    expenses = filter_queryset_by_branch_access(
        Expense.objects.filter(
            organization=organization,
            status=Expense.Status.APPROVED,
        ),
        request.user,
    )
    purchase_total = PurchaseItem.objects.filter(
        purchase__in=purchases,
    ).aggregate(
        total=Sum(F('quantity') * F('unit_cost'), output_field=DecimalField(max_digits=14, decimal_places=2))
    )['total']
    sales_total = sales.aggregate(total=Sum('grand_total', output_field=DecimalField(max_digits=14, decimal_places=2)))[
        'total'
    ]

    branch_queryset = organization.branches.filter(is_active=True, is_deleted=False)
    membership = get_active_membership(request.user, organization)
    if membership and not membership.has_all_branch_access:
        branch_queryset = branch_queryset.filter(id__in=membership.branches.values_list('id', flat=True))

    data = {
        'organization': organization.id,
        'branches': branch_queryset.count(),
        'products': organization.products.filter(is_active=True, is_deleted=False).count(),
        'customers': organization.customers.filter(is_active=True, is_deleted=False).count(),
        'suppliers': organization.suppliers.filter(is_active=True, is_deleted=False).count(),
        'inventory_units': decimal_sum(inventory.aggregate(total=Sum('quantity'))['total']),
        'low_stock_items': low_stock_items,
        'purchase_total': decimal_sum(purchase_total),
        'sales_total': decimal_sum(sales_total),
        'expenses_total': decimal_sum(expenses.aggregate(total=Sum('amount'))['total']),
    }
    serializer = OrganizationDashboardSerializer(data)
    return Response(serializer.data)
