from django.urls import path

from .consumers import (
    OrganizationConsumer,
    OrganizationInventoryConsumer,
    OrganizationPaymentConsumer,
    OrganizationPurchaseConsumer,
    OrganizationSaleConsumer,
)

websocket_urlpatterns = [
    path('ws/organizations/<int:organization_id>/', OrganizationConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/inventory/', OrganizationInventoryConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/purchases/', OrganizationPurchaseConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/sales/', OrganizationSaleConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/payments/', OrganizationPaymentConsumer.as_asgi()),
]
