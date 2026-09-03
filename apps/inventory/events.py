from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.notifications.event_types import EventType, build_realtime_event


def broadcast_stock_updated(stock, movement=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    event_type = EventType.INVENTORY_LOW_STOCK if stock.is_low_stock else EventType.INVENTORY_UPDATED
    event = build_realtime_event(
        event_type,
        stock.organization_id,
        {
            'id': stock.id,
            'inventory_id': stock.id,
            'organization': stock.organization_id,
            'branch': stock.branch_id,
            'branch_id': stock.branch_id,
            'product': stock.product_id,
            'product_id': stock.product_id,
            'product_variant': stock.product_variant_id,
            'variant_id': stock.product_variant_id,
            'quantity': str(stock.quantity),
            'reorder_level': str(stock.reorder_level),
            'is_low_stock': stock.is_low_stock,
            'previous_quantity': str(movement.previous_quantity) if movement else None,
            'movement_quantity': str(movement.quantity) if movement else None,
            'movement_type': movement.movement_type if movement else None,
        },
    )
    async_to_sync(channel_layer.group_send)(f'organization_{stock.organization_id}', event)
    async_to_sync(channel_layer.group_send)(f'organization_{stock.organization_id}_inventory', event)
