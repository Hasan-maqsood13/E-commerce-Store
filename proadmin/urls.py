from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminhome, name='adminhome'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('customers/', views.customerslist, name='customerslist'),
    path('customers/<int:user_id>/', views.customer_detail_view, name='customer_detail'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/edit/<int:user_id>/', views.edit_customer, name='edit_customer'),
    path('customers/data/<int:user_id>/', views.get_customer_data, name='get_customer_data'),
    path('customers/delete/<int:user_id>/', views.delete_customer, name='delete_customer'),
    path('notifications/', views.notifications, name="notifications"),
    path('notifications/mark-as-read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
]
