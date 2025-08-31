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
from datetime import datetime
from .models import *
import random
import stripe
import json
import re
from proadmin.views import *


# stripe.api_key = settings.STRIPE_TEST_SECRET_KEY  # Your Stripe secret key

def generate_verification_code(length=8):
    """Generate a random 4-digit numeric code"""
    return str(random.randint(1000, 9999))


#Create your Views here
def accountshome(request):
    return HttpResponse("Hello form accounts app page")

@csrf_exempt
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        remember_me = request.POST.get('remember_me') == 'on'
        
        errors = {}
        
        # Validate inputs
        if not email:
            errors['email'] = "Email is required."
        elif not '@' in email or not '.' in email:
            errors['email'] = "Please enter a valid email address."
        
        if not password:
            errors['password'] = "Password is required."
        
        if errors:
            return JsonResponse({'success': False, 'errors': errors})
        
        try:
            # Find user by email
            user = User.objects.get(email=email)
            
            # Check if user is active
            if not user.is_active:
                return JsonResponse({
                    'success': False, 
                    'message': 'Your account is inactive. Please contact support.'
                })
            
            # Check if user is verified
            if not user.is_verified:
                return JsonResponse({
                    'success': False, 
                    'message': 'Please verify your email before logging in.'
                })
            
            # Manually check password
            if check_password(password, user.password):
                # Manual login - set session variables
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['user_email'] = user.email
                request.session['user_role'] = user.role
                request.session['logged_in'] = True

                
                # Set session expiry based on remember_me
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    # Set session to expire in 2 weeks
                    request.session.set_expiry(1209600)  # 14 days in seconds
                
                # Update last login
                user.last_login = datetime.now()
                user.save()
                
                # Determine redirect URL based on user role
                if user.role == 'admin':
                    redirect_url = reverse('dashboard')
                else:
                    redirect_url = reverse('home')
                
                return JsonResponse({
                    'success': True, 
                    'message': 'Login successful!',
                    'redirect_url': redirect_url
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'message': 'Invalid password. Please try again.'
                })
                
        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'No account found with this email address.'
            })
    
    # For GET requests, render the login page
    return render(request, 'accounts/login.html')

@csrf_exempt
def logout_view(request):
    # Clear session data
    request.session.flush()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True, 
            'message': 'Logged out successfully.',
            'redirect_url': '/'
        })
    
    return redirect('home')


@csrf_exempt
def register(request):
    if request.method == 'POST':
        username = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        errors = {}
        
        # Username validation
        if not username:
            errors['name'] = "Name is required."
        elif not re.match(r'^[A-Za-z ]+$', username):
            errors['name'] = "Name can only contain letters and spaces."
        elif User.objects.filter(username=username).exists():
            errors['name'] = "This username is already taken."
        
        # Email validation
        if not email:
            errors['email'] = "Email is required."
        elif User.objects.filter(email=email).exists():
            errors['email'] = "This email is already registered."
        
        # Password validation
        if not password:
            errors['password'] = "Password is required."
        else:
            if len(password) < 8:
                errors['password'] = "Password must be at least 8 characters long."
            elif not re.search(r'[A-Z]', password):
                errors['password'] = "Password must contain at least one uppercase letter."
            elif not re.search(r'[a-z]', password):
                errors['password'] = "Password must contain at least one lowercase letter."
            elif not re.search(r'\d', password):
                errors['password'] = "Password must contain at least one digit."
            elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                errors['password'] = "Password must contain at least one special character."

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        try:
            verification_code = generate_verification_code()
            
            user = User.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                verification_token=verification_code
            )

            # Create notification for new customer registration
            create_notification(
                user=user,
                title="New Customer Registration",
                message=f"New customer {username} ({email}) has registered on the platform.",
                notification_type="New Customer"
            )

            # send_mail(
            #     'Verify Your Email',
            #     f'Hello {user.username},\n\nThank you for registering!\nYour verification code is: {verification_code}',
            #     'hasanmaqsood13@gmail.com', # Yahan apni email daalein
            #     [user.email],
            #     fail_silently=False,
            # )

            next_url = f"/accounts/verify-email/?email={user.email}"
            
            return JsonResponse({'success': True, 'next_url': next_url})

        except Exception as e:
            return JsonResponse({'success': False, 'errors': {'general': str(e)}})
    
    return render(request, 'accounts/register.html')

@csrf_exempt
def verify_email(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        code = request.POST.get('code', '').strip()
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'})
        
        # Code match karein
        if user.verification_token == code:
            user.is_verified = True
            user.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid verification code. Please try again.'})
            
    # GET request ke liye
    email_param = request.GET.get('email', '')
    if not email_param:
        return redirect('register')

    return render(request, 'accounts/emailverification.html')

@csrf_exempt
def resend_code(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        try:
            user = User.objects.get(email=email)
            
            # Naya verification code generate karein
            new_verification_code = generate_verification_code()
            user.verification_token = new_verification_code
            user.save()
            
            # Naya code email karein
            send_mail(
                'New Verification Code',
                f'Hello {user.username},\n\nA new verification code has been generated for you.\nYour new code is: {new_verification_code}',
                'hasanmaqsood13@gmail.com', # Yahan apni email daalein
                [user.email],
                fail_silently=False,
            )
            
            return JsonResponse({'success': True, 'message': 'A new code has been sent to your email.'})
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@csrf_exempt
def forgotpassword(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        try:
            user = User.objects.get(email=email)
            verification_code = generate_verification_code()
            user.verification_token = verification_code  # Using the same field for simplicity
            user.save()

            send_mail(
                'Password Reset Code',
                f'Hello {user.username},\n\nYour password reset code is: {verification_code}',
                'hasanmaqsood13@gmail.com',
                [user.email],
                fail_silently=False,
            )
            
            # Use session to pass email more securely
            request.session['forgot_password_email'] = email
            
            redirect_url = reverse('forgotpasswordemailverify')
            return JsonResponse({
                'success': True, 
                'message': 'A verification code has been sent to your email.', 
                'redirect_url': redirect_url
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'No account found with this email address.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'An error occurred: {str(e)}'
            })
    
    email_param = request.GET.get('email', '')
    context = {'email_param': email_param}
    return render(request, 'accounts/forgotpassword.html', context)

@csrf_exempt
def forgotpasswordemailverify(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        code = request.POST.get('code', '').strip()
        
        if 'forgot_password_email' not in request.session or request.session['forgot_password_email'] != email:
             return JsonResponse({'success': False, 'message': 'Invalid session. Please restart the process.'})

        try:
            user = User.objects.get(email=email)
            if user.verification_token == code:
                # Set a session flag to allow password reset
                request.session['password_reset_allowed'] = True
                redirect_url = reverse('resetpassword')
                return JsonResponse({'success': True, 'redirect_url': redirect_url})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid verification code. Please try again.'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'})
    
    email_param = request.GET.get('email', '')
    if not email_param and 'forgot_password_email' not in request.session:
        return redirect('forgotpassword')

    context = {'email_param': request.session.get('forgot_password_email', email_param)}
    return render(request, 'accounts/forgotpasswordemailverify.html', context)

@csrf_exempt
def resetpassword(request):
    # Check if user is allowed to reset password
    if 'password_reset_allowed' not in request.session or not request.session['password_reset_allowed']:
        # If not, redirect them to the start of the forgot password flow
        return redirect('forgotpassword')

    if request.method == 'POST':
        email = request.session.get('forgot_password_email')
        new_password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not email:
            return JsonResponse({'success': False, 'message': 'Session expired. Please restart the process.'})

        errors = {}
        if not new_password:
            errors['password'] = "Password is required."
        elif len(new_password) < 8:
            errors['password'] = "Password must be at least 8 characters long."
        elif not re.search(r'[A-Z]', new_password):
            errors['password'] = "Password must contain at least one uppercase letter."
        elif not re.search(r'[a-z]', new_password):
            errors['password'] = "Password must contain at least one lowercase letter."
        elif not re.search(r'\d', new_password):
            errors['password'] = "Password must contain at least one digit."
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            errors['password'] = "Password must contain at least one special character."
        
        if new_password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        try:
            user = User.objects.get(email=email)
            user.password = make_password(new_password)
            user.verification_token = None # Clear the token after use
            user.save()

            # Clear session flags
            del request.session['password_reset_allowed']
            del request.session['forgot_password_email']

            return JsonResponse({
                'success': True,
                'message': 'Password has been reset successfully. Please log in with your new password.',
                'redirect_url': reverse('login')
            })
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return render(request, 'accounts/resetpassword.html')