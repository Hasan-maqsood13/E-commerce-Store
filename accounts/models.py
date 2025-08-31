from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import CharField, DateField, DecimalField, ImageField
import uuid

#Create your models here
class User(models.Model):
    # Neccessary Info
    username = models.CharField(max_length=33, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    # Verification 
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    # Profile info
    firstname = models.CharField(max_length=100, blank=True, null=True)
    lastname = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # Account Management
    Role_choices = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )
    role = models.CharField(max_length=10, choices=Role_choices, default='customer')
    is_active = models.BooleanField(default=True)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.email} - {self.role}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    date_time = models.DateTimeField(default=timezone.now)

    STATUS_CHOICES = (
        ("Unread", "Unread"),
        ("Read", "Read"),
        ("Pending", "Pending"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Unread")

    TYPE_CHOICES = (
        ("Order Update", "Order Update"),
        ("Promotional", "Promotional"),
        ("Alert", "Alert"),
        ("System", "System"),
        ("New Customer", "New Customer"),  # Add this line
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="System")

    def __str__(self):
        return f"{self.title} ({self.status})"
