from django.urls import path

from .consumers import OrganizationConsumer, OrganizationInventoryConsumer

websocket_urlpatterns = [
    path('ws/organizations/<int:organization_id>/', OrganizationConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/inventory/', OrganizationInventoryConsumer.as_asgi()),
]
