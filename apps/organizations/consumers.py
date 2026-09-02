import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

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
        await self.send_json(
            {
                'type': 'organization.updated',
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
