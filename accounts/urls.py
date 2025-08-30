from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.accountshome, name='accountshome'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-code/', views.resend_code, name='resend_code'),
    path('logout/', views.logout_view, name='logout'),
    path('forgotpassword/', views.forgotpassword, name='forgotpassword'),
    path('forgotpasswordemailverify/', views.forgotpasswordemailverify, name='forgotpasswordemailverify'),
    path('resetpassword/', views.resetpassword, name='resetpassword'),
]
