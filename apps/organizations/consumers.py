import json

from channels.generic.websocket import AsyncWebsocketConsumer


class OrganizationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.organization_id = self.scope['url_route']['kwargs']['organization_id']
        self.group_name = f'organization_{self.organization_id}'

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

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))
