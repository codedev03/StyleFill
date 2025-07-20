from django.urls import path
from . import views
urlpatterns = [
    path('payments_success/', views.payments_success, name='payments_success'),
    path('checkout/', views.checkout, name='checkout'),
    path('billing_info/', views.billing_info, name='billing_info'),
    # path('process_order/', views.process_order, name='process_order'),
    path('my-orders/', views.track_orders, name='track_orders'),
    path('shipped_dash/', views.shipped_dash, name='shipped_dash'),
    path('not_shipped_dash/', views.not_shipped_dash, name='not_shipped_dash'),
    path('orders/<int:pk>/', views.orders, name='orders'),
    path('create-order/', views.create_order, name='create_order'),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
]