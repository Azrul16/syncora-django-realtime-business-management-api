"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.organizations.urls')),
    path('api/v1/', include('apps.branches.urls')),
    path('api/v1/', include('apps.products.urls')),
    path('api/v1/', include('apps.inventory.urls')),
    path('api/v1/', include('apps.suppliers.urls')),
    path('api/v1/', include('apps.purchases.urls')),
    path('api/v1/', include('apps.customers.urls')),
    path('api/v1/', include('apps.sales.urls')),
    path('api/v1/', include('apps.expenses.urls')),
    path('api/v1/', include('apps.finance.urls')),
    path('api/v1/', include('apps.notifications.urls')),
    path('api/v1/', include('apps.reports.urls')),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
