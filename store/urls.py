from django.urls import path
from.import views
urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('login/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout'),
    path('register/', views.register_user, name='register'),
    path('update_password/', views.update_password, name='update_password'),
    path('update_user/', views.update_user, name='update_user'),
    path('update_info/', views.update_info, name='update_info'),
    path('create_profile/', views.create_profile, name='create_profile'),  # Ensure this is included
    path('product/<int:pk>/', views.product, name='product'),
    path('category/<str:cat>/', views.category, name='category'),
    path('category_summary/', views.category_summary, name='category_summary'),
    path('search/', views.search, name='search'),
    path('delete-account/', views.delete_account, name='delete_account'),
]