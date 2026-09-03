from django.urls import path

from . import views

urlpatterns = [
    path('auth/login/', views.login, name='auth-login'),
    path('auth/logout/', views.logout, name='auth-logout'),
    path('auth/change-password/', views.change_password, name='auth-change-password'),
    path('auth/me/', views.me, name='auth-me'),
]
