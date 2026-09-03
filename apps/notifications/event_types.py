from django.utils import timezone


class EventType:
    ORGANIZATION_UPDATED = 'organization.updated'
    INVENTORY_UPDATED = 'inventory.updated'
    INVENTORY_LOW_STOCK = 'inventory.low_stock'
    PURCHASE_ORDERED = 'purchase.ordered'
    PURCHASE_RECEIVED = 'purchase.received'
    PURCHASE_CANCELLED = 'purchase.cancelled'
    SALE_CONFIRMED = 'sale.confirmed'
    SALE_COMPLETED = 'sale.completed'
    SALE_CANCELLED = 'sale.cancelled'
    PAYMENT_CREATED = 'payment.created'
    EXPENSE_APPROVED = 'expense.approved'
    EXPENSE_REJECTED = 'expense.rejected'
    FINANCE_UPDATED = 'finance.updated'
    NOTIFICATION_CREATED = 'notification.created'


def build_realtime_event(event, organization_id, data=None):
    return {
        'type': 'realtime.event',
        'event': event,
        'timestamp': timezone.now().isoformat(),
        'organization_id': organization_id,
        'data': data or {},
    }
