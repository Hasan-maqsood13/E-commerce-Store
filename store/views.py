from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from ecommerce_store.settings import EMAIL_HOST_USER
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from django.core.mail import send_mail
from django.utils.text import slugify
from django.core import serializers
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from urllib.parse import unquote
from django.db.models import Sum
from django.urls import reverse
from datetime import timedelta
from datetime import datetime
from .models import *
from accounts.models import User
import random
import stripe
import json
import re


# stripe.api_key = settings.STRIPE_TEST_SECRET_KEY  # Your Stripe secret key

def generate_verification_code(length=8):
    """Generate a random 4-digit numeric code"""
    return str(random.randint(1000, 9999))


#Create your Views here
def home(request):
    context = {}
    if request.session.get('logged_in'):
        try:
            user_id = request.session.get('user_id')
            user = User.objects.get(id=user_id)
            context['user'] = user
        except User.DoesNotExist:
            pass
    return render(request, 'store/shop.html', context)


def userprofile(request):
    # Agar user login nahi hai, to usko login page par bhej dein
    if not request.session.get('logged_in'):
        return redirect('login')

    user_id = request.session.get('user_id')
    user = get_object_or_404(User, id=user_id) # Agar user exist nahi karta to 404 error dega

    if request.method == 'POST':
        # Form se data get karein
        firstname = request.POST.get('firstname', '').strip()
        lastname = request.POST.get('lastname', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        country = request.POST.get('country', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()


        # Validation checks
        if not firstname or not lastname or not username or not email:
            messages.error(request, 'First Name, Last Name, Display Name, and Email are required.')
        elif User.objects.filter(username=username).exclude(id=user.id).exists():
            messages.error(request, 'This username is already taken.')
        elif User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, 'This email is already registered.')
        else:
            # All validation passed, update user object
            user.firstname = firstname
            user.lastname = lastname
            user.username = username
            user.email = email
            user.phone_number = phone_number
            user.address = address
            user.city = city
            user.country = country
            user.postal_code = postal_code

            user.last_updated = timezone.now()
            user.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('userprofile')

    context = {'user': user}
    return render(request, 'store/userprofile.html', context)