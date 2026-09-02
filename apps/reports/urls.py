from django.urls import path

from .views import organization_dashboard

urlpatterns = [
    path('organizations/<int:organization_id>/dashboard/', organization_dashboard, name='organization-dashboard'),
]
