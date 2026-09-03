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
    path('dashboard/profit-trend/', views.dashboard_profit_trend, name='dashboard-profit-trend'),
    path('dashboard/top-products/', views.dashboard_top_products, name='dashboard-top-products'),
    path('dashboard/slow-moving-products/', views.dashboard_slow_moving_products, name='dashboard-slow-moving-products'),
    path('dashboard/inventory-summary/', views.dashboard_inventory_summary, name='dashboard-inventory-summary'),
    path('dashboard/low-stock/', views.dashboard_low_stock, name='dashboard-low-stock'),
    path('dashboard/out-of-stock/', views.dashboard_out_of_stock, name='dashboard-out-of-stock'),
    path('dashboard/stock-value/', views.dashboard_stock_value, name='dashboard-stock-value'),
    path('dashboard/branches/', views.dashboard_branches, name='dashboard-branches'),
    path('dashboard/customers/', views.dashboard_customers, name='dashboard-customers'),
    path('dashboard/suppliers/', views.dashboard_suppliers, name='dashboard-suppliers'),
]
