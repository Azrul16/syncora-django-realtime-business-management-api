from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.models import Organization
from apps.organizations.permissions import get_active_membership

from .services.financial_summary import FinancialSummaryService


def serialize_money(value):
    if isinstance(value, Decimal):
        return f'{value:.2f}'
    if isinstance(value, dict):
        return {key: serialize_money(item) for key, item in value.items()}
    return value


def get_organization_for_request(request):
    organization_id = request.query_params.get('organization')
    if not organization_id:
        raise ValidationError({'organization': 'This query parameter is required.'})

    organization = Organization.objects.filter(id=organization_id).first()
    if not organization or not get_active_membership(request.user, organization):
        raise NotFound('Organization was not found.')
    return organization


def get_financial_service(request):
    organization = get_organization_for_request(request)
    return FinancialSummaryService(organization=organization)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finance_summary(request):
    service = get_financial_service(request)
    return Response(serialize_money(service.get_summary()))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_summary(request):
    service = get_financial_service(request)
    return Response(serialize_money(service.get_sales_summary()))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expense_summary(request):
    service = get_financial_service(request)
    return Response(serialize_money(service.get_expense_summary()))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profit_summary(request):
    service = get_financial_service(request)
    return Response(serialize_money(service.get_profit_summary()))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cash_flow_summary(request):
    service = get_financial_service(request)
    return Response(serialize_money(service.get_cash_flow_summary()))

