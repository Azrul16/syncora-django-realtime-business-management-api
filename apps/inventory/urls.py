from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InventoryStockViewSet, StockMovementViewSet

router = DefaultRouter()
router.register('inventory', InventoryStockViewSet, basename='inventory')
router.register('inventory-stocks', InventoryStockViewSet, basename='inventory-stock')
router.register('stock-movements', StockMovementViewSet, basename='stock-movement')

urlpatterns = [
    path('', include(router.urls)),
]
