from django.urls import path
from . import views
urlpatterns = [
    path('', views.experience_list, name='experience_list'),
    path('<int:pk>/', views.experience_detail, name='experience_detail'),
    path('<int:pk>/book/', views.book_experience, name='book_experience'),
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path("request-refund/<int:booking_id>/", views.request_refund, name="request_refund"),
]