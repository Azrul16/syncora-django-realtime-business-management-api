import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.branches.models import Branch

from .models import OrganizationMembership


class OrganizationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def organization_updated(self, event):
        await self.send_json({'event': 'organization.updated', 'data': event['data']})

    async def realtime_event(self, event):
        await self.send_json(
            {
                'event': event['event'],
                'timestamp': event['timestamp'],
                'organization_id': event['organization_id'],
                'data': event['data'],
            }
        )

    async def inventory_stock_updated(self, event):
        await self.send_json(
            {
                'type': 'inventory.stock_updated',
                'data': event['data'],
            }
        )

    async def purchase_event(self, event):
        await self.send_json(
            {
                'type': event['data']['event'],
                'data': event['data'],
            }
        )

    async def sale_event(self, event):
        await self.send_json(
            {
                'type': event['data']['event'],
                'data': event['data'],
            }
        )

    async def payment_event(self, event):
        await self.send_json(
            {
                'type': event['data']['event'],
                'data': event['data'],
            }
        )

    async def finance_event(self, event):
        await self.send_json(
            {
                'type': event['data']['event'],
                'data': event['data'],
            }
        )

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

    @database_sync_to_async
    def can_connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            return False

        return OrganizationMembership.objects.filter(
            user=user,
            organization_id=self.organization_id,
            is_active=True,
        ).exists()


class OrganizationInventoryConsumer(OrganizationConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'
        self.inventory_group_name = f'organization_{self.organization_id}_inventory'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.inventory_group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.inventory_group_name, self.channel_name)


class OrganizationPurchaseConsumer(OrganizationConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'
        self.purchase_group_name = f'organization_{self.organization_id}_purchases'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.purchase_group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.purchase_group_name, self.channel_name)


class OrganizationSaleConsumer(OrganizationConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'
        self.sale_group_name = f'organization_{self.organization_id}_sales'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.sale_group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.sale_group_name, self.channel_name)


class OrganizationPaymentConsumer(OrganizationConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'
        self.payment_group_name = f'organization_{self.organization_id}_payments'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.payment_group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.payment_group_name, self.channel_name)


class OrganizationFinanceConsumer(OrganizationConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'
        self.finance_group_name = f'organization_{self.organization_id}_finance'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.finance_group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.finance_group_name, self.channel_name)


class OrganizationDashboardConsumer(OrganizationConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'
        self.dashboard_group_name = f'organization_{self.organization_id}_dashboard'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.dashboard_group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.dashboard_group_name, self.channel_name)


class OrganizationBranchConsumer(OrganizationConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.branch_id = self.scope['url_route']['kwargs']['branch_id']
        self.group_name = f'organization_{self.organization_id}'
        self.branch_group_name = f'organization_{self.organization_id}_branch_{self.branch_id}'

        if not await self.can_connect():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.branch_group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.branch_group_name, self.channel_name)

    @database_sync_to_async
    def can_connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            return False

        return OrganizationMembership.objects.filter(
            user=user,
            organization_id=self.organization_id,
            is_active=True,
        ).exists() and Branch.objects.filter(
            id=self.branch_id,
            organization_id=self.organization_id,
        ).exists()


class UserNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'user_{self.user_id}_notifications'

        user = self.scope.get('user')
        if not user or not user.is_authenticated or user.id != self.user_id:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection.ready'})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def realtime_event(self, event):
        await self.send_json(
            {
                'event': event['event'],
                'timestamp': event['timestamp'],
                'organization_id': event['organization_id'],
                'data': event['data'],
            }
        )

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))
