from decimal import Decimal

from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.branches.models import Branch
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
    branch = get_branch_for_request(request, organization)
    date_from = get_date_for_request(request, 'date_from')
    date_to = get_date_for_request(request, 'date_to')
    if date_from and date_to and date_from > date_to:
        raise ValidationError({'date_to': 'date_to must be on or after date_from.'})
    return FinancialSummaryService(
        organization=organization,
        date_from=date_from,
        date_to=date_to,
        branch=branch,
    )


def get_branch_for_request(request, organization):
    branch_id = request.query_params.get('branch')
    if not branch_id:
        return None
    branch = Branch.objects.filter(id=branch_id, organization=organization).first()
    if not branch:
        raise NotFound('Branch was not found.')
    return branch


def get_date_for_request(request, name):
    value = request.query_params.get(name)
    if not value:
        return None
    parsed = parse_date(value)
    if not parsed:
        raise ValidationError({name: 'Use YYYY-MM-DD date format.'})
    return parsed


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
