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
from Products.models import *
import random
import stripe
import json
import re

stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

# stripe.api_key = settings.STRIPE_TEST_SECRET_KEY  # Your Stripe secret key

def generate_verification_code(length=8):
    """Generate a random 4-digit numeric code"""
    return str(random.randint(1000, 9999))


# Update your home view
def home(request):
    context = {}
    
    # Handle session
    if not request.session.session_key:
        request.session.create()
    
    # Check if user is logged in via session (your custom login system)
    if 'logged_in' in request.session and request.session['logged_in']:
        try:
            user_id = request.session.get('user_id')
            # If you have a custom User model, use it here
            # user = YourUserModel.objects.get(id=user_id)
            # context['user'] = user
            context['user'] = {'username': request.session.get('username', 'User')}
        except:
            request.session['logged_in'] = False
            request.session['user_id'] = None
    
    # Get wishlist product IDs for current session
    session_key = request.session.session_key
    wishlist_product_ids = Wishlist.objects.filter(
        session_key=session_key
    ).values_list('product_id', flat=True)
    
    context['wishlist_product_ids'] = list(wishlist_product_ids)
    
    # Fetching only the unique, top-level categories
    top_level_categories = Category.objects.filter(parent__isnull=True, is_active=True).distinct()
    context['categories'] = top_level_categories
    
    # Get all products for different sections
    new_arrival_products = Product.objects.filter(tag='new_arrival', is_active=True).distinct()
    context['new_arrival_products'] = new_arrival_products
    context['new_arrival_count'] = new_arrival_products.count()
    
    best_seller_products = Product.objects.filter(tag='best_seller', is_active=True).distinct()
    context['best_seller_products'] = best_seller_products
    context['best_seller_count'] = best_seller_products.count()
    
    featured_products = Product.objects.filter(tag='featured', is_active=True).distinct()
    context['featured_products'] = featured_products
    context['featured_count'] = featured_products.count()
    
    special_offer_products = Product.objects.filter(tag='special_offer', is_active=True).distinct()
    context['special_offer_products'] = special_offer_products
    context['special_offer_count'] = special_offer_products.count()
    
    top_rated_products = Product.objects.filter(tag='top_rated', is_active=True).distinct()
    context['top_rated_products'] = top_rated_products
    context['top_rated_count'] = top_rated_products.count()
    
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


def cart(request):
    user_id = request.session.get('user_id')
    cart_items = Cart.objects.filter(user_id=user_id)

    subtotal = 0
    for item in cart_items:
        item.item_total = item.product.price * item.quantity
        subtotal += item.item_total

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'grand_total': subtotal,
    }
    return render(request, 'store/cart.html', context)

def add_to_cart(request, product_id):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    product = get_object_or_404(Product, id=product_id)
    
    cart_item, created = Cart.objects.get_or_create(
        user=user,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"Updated {product.name} quantity to {cart_item.quantity}")
    else:
        messages.success(request, f"Added {product.name} to your cart")
    
    return redirect('cart')

def update_cart(request, item_id):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    cart_item = get_object_or_404(Cart, id=item_id, user=user)
    
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid quantity'}, status=400)
            
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            
            new_total = sum(item.total_price() for item in Cart.objects.filter(user=user))
            
            return JsonResponse({
                'status': 'success',
                'item_total': cart_item.total_price(),
                'new_total': new_total,
                'new_quantity': cart_item.quantity,
                'message': "Cart updated successfully"
            })
        else:
            cart_item.delete()
            new_total = sum(item.total_price() for item in Cart.objects.filter(user=user))
            return JsonResponse({
                'status': 'success',
                'new_total': new_total,
                'message': "Item removed from cart"
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def remove_from_cart(request, item_id):
    # ... (existing code for remove_from_cart)
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    cart_item = get_object_or_404(Cart, id=item_id, user=user)
    cart_item.delete()
    messages.success(request, "Item removed from cart")
    return redirect('cart')


def checkoutpage(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Please login to checkout")
        return redirect('login')  # Assuming you have a login URL
    
    user = get_object_or_404(User, id=user_id)
    cart_items = Cart.objects.filter(user=user)
    
    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect('cart')
    
    # Calculate totals
    subtotal = sum(item.total_price() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'grand_total': subtotal,  # Assuming no shipping/taxes for now
        'user': user
    }
    
    return render(request, 'store/checkout.html', context)

# views.py (store app)
def place_order(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'status': 'error', 'message': 'User not logged in'})
        
        user = get_object_or_404(User, id=user_id)
        cart_items = Cart.objects.filter(user=user)
        
        if not cart_items.exists():
            return JsonResponse({'status': 'error', 'message': 'Cart is empty'})
        
        # Get form data
        full_name = f"{request.POST.get('fname')} {request.POST.get('lname')}"
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('billing_address')
        city = request.POST.get('city')
        postal_code = request.POST.get('zipcode')
        payment_method = request.POST.get('payment_method')
        
        # Calculate total amount
        total_amount = sum(item.total_price() for item in cart_items)
        
        # Create order
        order = Order.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            postal_code=postal_code,
            payment_method=payment_method,
            total_amount=total_amount
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
        
        # Handle payment based on method
        if payment_method == 'COD':
            # Clear cart
            cart_items.delete()
            messages.success(request, "Order placed successfully!")
            return redirect('home')
        elif payment_method == 'Stripe':
            # Here you would implement Stripe payment
            # For now, we'll just redirect to a placeholder
            return redirect('stripe_checkout', order_id=order.id)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def stripe_checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, user_id=request.session.get('user_id'))
    
    # Set your Stripe API key
    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
    
    try:
        # Check if customer exists, create if not
        if not order.user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=order.email,
                name=order.full_name,
                metadata={'user_id': order.user.id}
            )
            order.user.stripe_customer_id = customer.id
            order.user.save()
        else:
            customer = stripe.Customer.retrieve(order.user.stripe_customer_id)
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Order #{order.id}',
                        },
                        'unit_amount': int(order.total_amount * 100),  # Convert to cents
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=request.build_absolute_uri(f'/order-success/{order.id}/'),
            cancel_url=request.build_absolute_uri(f'/order-cancel/{order.id}/'),
            metadata={'order_id': order.id}
        )
        
        return redirect(checkout_session.url)
    
    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
        return redirect('checkoutpage')

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user_id=request.session.get('user_id'))
    order.payment_status = True
    order.status = 'Processing'
    order.save()
    
    # Clear cart
    Cart.objects.filter(user_id=request.session.get('user_id')).delete()
    
    messages.success(request, "Payment successful! Your order has been placed.")
    return redirect('home')

def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user_id=request.session.get('user_id'))
    order.status = 'Cancelled'
    order.save()
    
    messages.warning(request, "Payment was cancelled.")
    return redirect('cart')
