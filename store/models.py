from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import CharField, DateField, DecimalField, ImageField
import uuid
from accounts.models import *
from Products.models import *

#Create your models here
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='carted_by')
    quantity = models.PositiveIntegerField(default=1)
    added_on = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'product')  # prevent duplicate cart entries

    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.quantity})"