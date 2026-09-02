from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_purchase_event(purchase, event_type):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    event = {
        'type': 'purchase.event',
        'data': {
            'event': event_type,
            'purchase_id': purchase.id,
            'purchase_number': purchase.purchase_number,
            'supplier': purchase.supplier.name,
            'branch': purchase.branch_id,
            'status': purchase.status,
            'total': str(purchase.grand_total),
        },
    }
    async_to_sync(channel_layer.group_send)(f'organization_{purchase.organization_id}', event)
    async_to_sync(channel_layer.group_send)(f'organization_{purchase.organization_id}_purchases', event)
