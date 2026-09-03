from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import InventoryStock, StockMovement
from apps.notifications.event_types import EventType
from apps.notifications.services.event_dispatcher import dispatch_event


def increase_stock(*, branch, quantity, product_variant=None, product=None, movement_type=None, reference='', note='', user=None):
    movement_type = movement_type or StockMovement.MovementType.ADJUSTMENT_IN
    return change_stock(
        branch=branch,
        quantity=quantity,
        product_variant=product_variant,
        product=product,
        movement_type=movement_type,
        reference=reference,
        note=note,
        user=user,
        direction=1,
    )


def decrease_stock(*, branch, quantity, product_variant=None, product=None, movement_type=None, reference='', note='', user=None):
    movement_type = movement_type or StockMovement.MovementType.ADJUSTMENT_OUT
    return change_stock(
        branch=branch,
        quantity=quantity,
        product_variant=product_variant,
        product=product,
        movement_type=movement_type,
        reference=reference,
        note=note,
        user=user,
        direction=-1,
    )


def adjust_stock(*, stock, new_quantity, reference='', note='', user=None):
    quantity = Decimal(str(new_quantity)) - stock.quantity
    if quantity >= 0:
        return increase_stock(
            branch=stock.branch,
            product_variant=stock.product_variant,
            product=stock.product,
            quantity=quantity,
            reference=reference,
            note=note,
            user=user,
        )
    return decrease_stock(
        branch=stock.branch,
        product_variant=stock.product_variant,
        product=stock.product,
        quantity=abs(quantity),
        reference=reference,
        note=note,
        user=user,
    )


@transaction.atomic
def change_stock(*, branch, quantity, product_variant=None, product=None, movement_type, reference='', note='', user=None, direction):
    quantity = Decimal(str(quantity))
    if quantity <= 0:
        raise ValidationError('Quantity must be greater than zero.')
    if not product_variant and not product:
        raise ValidationError('A product or product variant is required.')

    organization = branch.organization
    if product_variant:
        product = product_variant.product
    if product.organization_id != organization.id:
        raise ValidationError('Inventory item must belong to the branch organization.')

    stock, _ = (
        InventoryStock.objects.select_for_update().get_or_create(
            branch=branch,
            product_variant=product_variant,
            product=product,
            defaults={'organization': organization, 'quantity': 0},
        )
    )
    previous_quantity = stock.quantity
    new_quantity = previous_quantity + (quantity * direction)
    if new_quantity < 0:
        raise ValidationError('Inventory quantity cannot go below zero.')

    stock.organization = organization
    stock.quantity = new_quantity
    stock.updated_by = user if getattr(user, 'is_authenticated', False) else None
    stock.save(update_fields=['organization', 'quantity', 'updated_by', 'updated_at'])

    movement = StockMovement.objects.create(
        organization=organization,
        branch=branch,
        product_variant=product_variant,
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        reference=reference,
        note=note,
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    event = EventType.INVENTORY_LOW_STOCK if stock.is_low_stock else EventType.INVENTORY_UPDATED
    dispatch_event(
        event=event,
        organization=organization,
        actor=user,
        resource=stock,
        branch=branch,
        data={
            'inventory_id': stock.id,
            'branch_id': stock.branch_id,
            'product_id': stock.product_id,
            'variant_id': stock.product_variant_id,
            'quantity': str(stock.quantity),
            'reorder_level': str(stock.reorder_level),
            'is_low_stock': stock.is_low_stock,
            'previous_quantity': str(movement.previous_quantity),
            'movement_quantity': str(movement.quantity),
            'movement_type': movement.movement_type,
        },
        groups=[f'organization_{organization.id}_inventory'],
        notification_title='Low stock detected' if stock.is_low_stock else '',
        notification_message=f'{stock.product} stock is now {stock.quantity}.' if stock.is_low_stock else '',
        activity_description=f'Inventory updated for {stock.product}.',
    )
    return stock, movement
