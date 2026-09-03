from django.urls import path

from .consumers import (
    OrganizationConsumer,
    OrganizationBranchConsumer,
    OrganizationDashboardConsumer,
    OrganizationFinanceConsumer,
    OrganizationInventoryConsumer,
    OrganizationPaymentConsumer,
    OrganizationPurchaseConsumer,
    OrganizationSaleConsumer,
    UserNotificationConsumer,
)

websocket_urlpatterns = [
    path('ws/organizations/<int:organization_id>/', OrganizationConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/inventory/', OrganizationInventoryConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/purchases/', OrganizationPurchaseConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/sales/', OrganizationSaleConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/payments/', OrganizationPaymentConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/finance/', OrganizationFinanceConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/dashboard/', OrganizationDashboardConsumer.as_asgi()),
    path('ws/organizations/<int:organization_id>/branches/<int:branch_id>/', OrganizationBranchConsumer.as_asgi()),
    path('ws/users/<int:user_id>/notifications/', UserNotificationConsumer.as_asgi()),
]
