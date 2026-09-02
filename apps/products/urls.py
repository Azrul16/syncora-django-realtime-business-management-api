from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductCategoryViewSet, ProductVariantViewSet, ProductViewSet

router = DefaultRouter()
router.register('categories', ProductCategoryViewSet, basename='category')
router.register('products', ProductViewSet, basename='product')
router.register('product-variants', ProductVariantViewSet, basename='product-variant')

urlpatterns = [
    path('', include(router.urls)),
]
