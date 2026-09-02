from django.urls import path

from .consumers import OrganizationConsumer

websocket_urlpatterns = [
    path('ws/organizations/<int:organization_id>/', OrganizationConsumer.as_asgi()),
]
