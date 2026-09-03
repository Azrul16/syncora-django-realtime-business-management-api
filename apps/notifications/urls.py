from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityLogViewSet, NotificationViewSet

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notification')
router.register('activities', ActivityLogViewSet, basename='activity')

urlpatterns = [
    path('', include(router.urls)),
]
