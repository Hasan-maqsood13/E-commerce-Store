from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.userprofile, name='userprofile'),
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkoutpage, name='checkoutpage'),
    path('place-order/', views.place_order, name='place_order'),
    path('stripe-checkout/<int:order_id>/', views.stripe_checkout, name='stripe_checkout'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('order-cancel/<int:order_id>/', views.order_cancel, name='order_cancel'),
]
