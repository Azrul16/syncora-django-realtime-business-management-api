from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_stock_updated(stock):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f'organization_{stock.organization_id}',
        {
            'type': 'inventory.stock_updated',
            'data': {
                'id': stock.id,
                'organization': stock.organization_id,
                'branch': stock.branch_id,
                'product': stock.product_id,
                'quantity': str(stock.quantity),
                'reorder_level': str(stock.reorder_level),
                'is_low_stock': stock.is_low_stock,
            },
        },
    )
