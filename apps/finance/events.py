from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .services.financial_summary import FinancialSummaryService


def serialize_money(value):
    if isinstance(value, Decimal):
        return f'{value:.2f}'
    if isinstance(value, dict):
        return {key: serialize_money(item) for key, item in value.items()}
    return value


def broadcast_finance_update(organization, reason):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    service = FinancialSummaryService(organization=organization)
    event = {
        'type': 'finance.event',
        'data': {
            'event': 'finance.updated',
            'reason': reason,
            'organization_id': organization.id,
            'summary': serialize_money(service.get_summary()),
        },
    }
    async_to_sync(channel_layer.group_send)(f'organization_{organization.id}', event)
    async_to_sync(channel_layer.group_send)(f'organization_{organization.id}_finance', event)

