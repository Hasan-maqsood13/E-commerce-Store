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
from django.db import IntegrityError
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
import random
import stripe
import json
import re
from accounts.models import User
from accounts.models import Notification


# stripe.api_key = settings.STRIPE_TEST_SECRET_KEY  # Your Stripe secret key

def generate_verification_code(length=8):
    """Generate a random 4-digit numeric code"""
    return str(random.randint(1000, 9999))


#Create your Views here
def adminhome(request):
    return HttpResponse("Hemlooo Geeee")

def dashboard(request):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return redirect('login') 

    try:
        user_id = request.session.get('user_id')
        user = User.objects.get(id=user_id)
        
        context = {
            'username': user.firstname or user.username,
        }
        
        return render(request, 'proadmin/dashboard.html', context)
        
    except User.DoesNotExist:
        request.session.flush()
        return redirect('login')
    

def customerslist(request):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return redirect('login')
    
    customers = User.objects.filter(role='customer').order_by('-date_joined')
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    
    context = {
        'customers': customers,
        'username': user.firstname or user.username,
    }
    
    return render(request, 'proadmin/customerslist.html', context)

def customer_detail_view(request, user_id):
    # Fetch the user object or return a 404 error if not found
    customer = get_object_or_404(User, id=user_id)
    
    
    # Context to pass to the template
    context = {
        'customer': customer
    }
    
    return render(request, 'proadmin/customerdetailpage.html', context)

def add_customer(request):
    # Check if the user is an authenticated admin
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return redirect('login')

    if request.method == 'POST':
        # Get data from the form
        username = request.POST.get('username')
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')

        try:
            # Create a new User instance
            user = User.objects.create(
                username=username,
                email=email,
                password=password, # You should hash this password!
                firstname=firstname,
                lastname=lastname,
                phone_number=phone_number,
                role='customer', # Set the role to 'customer'
                is_active=True,
                is_verified=False, # Set to False by default
                verification_token=str(random.randint(1000, 9999)) # Example token
            )
            # Create notification for admin-added customer
            create_notification(
                user=user,
                title="Admin Added New Customer",
                message=f"Admin added new customer {username} ({email}) to the system.",
                notification_type="New Customer"
            )
            messages.success(request, 'Customer added successfully!')
        except IntegrityError:
            messages.error(request, 'Username or email already exists. Please choose a different one.')
        
    return redirect('customerslist')

def edit_customer(request, user_id):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return redirect('login')
    
    customer = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Get data from the form
        username = request.POST.get('username')
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        country = request.POST.get('country')
        postal_code = request.POST.get('postal_code')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            # Update the customer instance
            customer.username = username
            customer.firstname = firstname
            customer.lastname = lastname
            customer.email = email
            customer.phone_number = phone_number
            customer.address = address
            customer.city = city
            customer.country = country
            customer.postal_code = postal_code
            customer.is_active = is_active
            customer.last_updated = timezone.now()
            
            customer.save()
            messages.success(request, 'Customer updated successfully!')
            return redirect('customerslist')
        except IntegrityError:
            messages.error(request, 'Username or email already exists. Please choose a different one.')
    
    # If GET request or form invalid, return to customer list
    return redirect('customerslist')


def get_customer_data(request, user_id):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        customer = User.objects.get(id=user_id)
        data = {
            'id': customer.id,
            'username': customer.username,
            'firstname': customer.firstname,
            'lastname': customer.lastname,
            'email': customer.email,
            'phone_number': customer.phone_number,
            'address': customer.address,
            'city': customer.city,
            'country': customer.country,
            'postal_code': customer.postal_code,
            'is_active': customer.is_active,
        }
        return JsonResponse(data)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
    
def delete_customer(request, user_id):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    try:
        customer = User.objects.get(id=user_id)
        customer.delete()
        messages.success(request, 'Customer deleted successfully!')
        return JsonResponse({'success': True})
    except User.DoesNotExist:
        messages.error(request, 'Customer not found!')
        return JsonResponse({'success': False, 'error': 'Customer not found'}, status=404)
    except Exception as e:
        messages.error(request, f'Error deleting customer: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
def notifications(request):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return redirect('login')
    
    # Get all notifications, ordered by most recent first
    notifications_list = Notification.objects.all().order_by('-date_time')
    
    context = {
        'notifications': notifications_list
    }
    
    return render(request, 'proadmin/notifications.html', context)

def create_notification(user, title, message, notification_type="System"):
    """
    Utility function to create notifications
    """
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type
    )

def mark_notification_as_read(request, notification_id):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.status = 'Read'
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

def delete_notification(request, notification_id):
    if not request.session.get('logged_in') or request.session.get('user_role') != 'admin':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.delete()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)