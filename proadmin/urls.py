from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminhome, name='adminhome'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
