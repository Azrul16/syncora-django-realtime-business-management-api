from django.urls import path

from . import views

urlpatterns = [
    path('finance/summary/', views.finance_summary, name='finance-summary'),
    path('finance/sales-summary/', views.sales_summary, name='finance-sales-summary'),
    path('finance/expense-summary/', views.expense_summary, name='finance-expense-summary'),
    path('finance/profit-summary/', views.profit_summary, name='finance-profit-summary'),
    path('finance/cash-flow/', views.cash_flow_summary, name='finance-cash-flow'),
    path('dashboard/summary/', views.dashboard_summary, name='dashboard-summary'),
    path('dashboard/sales-trend/', views.dashboard_sales_trend, name='dashboard-sales-trend'),
]
