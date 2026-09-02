from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_sale_event(sale, event_type):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    event = {
        'type': 'sale.event',
        'data': {
            'event': event_type,
            'sale_id': sale.id,
            'sale_number': sale.sale_number,
            'branch_id': sale.branch_id,
            'customer_id': sale.customer_id,
            'status': sale.status,
            'total': str(sale.grand_total),
            'payment_status': sale.payment_status,
            'paid_amount': str(sale.paid_amount),
            'due_amount': str(sale.due_amount),
        },
    }
    async_to_sync(channel_layer.group_send)(f'organization_{sale.organization_id}', event)
    async_to_sync(channel_layer.group_send)(f'organization_{sale.organization_id}_sales', event)


def broadcast_payment_event(payment):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    sale = payment.sale
    event = {
        'type': 'payment.event',
        'data': {
            'event': 'payment.created',
            'payment_id': payment.id,
            'sale_id': sale.id,
            'sale_number': sale.sale_number,
            'amount': str(payment.amount),
            'payment_method': payment.payment_method,
            'payment_status': sale.payment_status,
            'paid_amount': str(sale.paid_amount),
            'due_amount': str(sale.due_amount),
        },
    }
    async_to_sync(channel_layer.group_send)(f'organization_{sale.organization_id}', event)
    async_to_sync(channel_layer.group_send)(f'organization_{sale.organization_id}_payments', event)
