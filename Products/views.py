from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
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

# Create your views here.
def productshome(request):
    return HttpResponse("hello from Products app!")

# This view is for listing categories and handling GET requests
def categories(request):
    categories_list = Category.objects.all()
    
    context = {
        'categories': categories_list,
    }
    return render(request, 'products/categories.html', context)

def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        parent_id = request.POST.get('parent')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')

        if Category.objects.filter(name=name).exists():
            messages.error(request, "A category with this name already exists.")
            return redirect('categories')
        
        parent = None
        if parent_id:
            try:
                parent = Category.objects.get(id=parent_id)
            except Category.DoesNotExist:
                messages.error(request, "Parent category not found.")
                return redirect('categories')
        
        new_category = Category(
            name=name,
            description=description,
            parent=parent,
            is_active=is_active,
            image=image
        )
        new_category.save()
        messages.success(request, "Category added successfully.")
        return redirect('categories')
    return redirect('categories')

def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        parent_id = request.POST.get('parent')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')
        
        # Check if name is changed and if it already exists (excluding current category)
        if name != category.name and Category.objects.filter(name=name).exclude(id=category_id).exists():
            messages.error(request, "A category with this name already exists.")
            return redirect('categories')
        
        parent = None
        if parent_id:
            try:
                parent = Category.objects.get(id=parent_id)
                # Prevent a category from being its own parent
                if parent.id == category_id:
                    messages.error(request, "A category cannot be its own parent.")
                    return redirect('categories')
            except Category.DoesNotExist:
                messages.error(request, "Parent category not found.")
                return redirect('categories')
        
        category.name = name
        category.description = description
        category.parent = parent
        category.is_active = is_active
        
        if image:
            category.image = image
            
        category.save()
        messages.success(request, "Category updated successfully.")
        return redirect('categories')
    
    # If not POST, redirect to categories page
    return redirect('categories')

def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        # Check if category has subcategories
        if category.subcategories.exists():
            messages.error(request, "Cannot delete category with subcategories. Please delete subcategories first.")
            return redirect('categories')
            
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect('categories')
    
    # If not POST, redirect to categories page
    return redirect('categories')

def product(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    tag_choices = Product.PRODUCT_TAG_CHOICES
    return render(request, "Products/products.html", {
        "products": products,
        "categories": categories,
        "tag_choices": tag_choices
    })



def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        tag = request.POST.get('tag')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')

        if Product.objects.filter(name=name).exists():
            messages.error(request, "A product with this name already exists.")
            return redirect('products')

        category = None
        if category_id:
            category = get_object_or_404(Category, id=category_id)

        Product.objects.create(
            name=name,
            description=description,
            category=category,
            price=price,
            stock=stock,
            tag=tag,
            is_active=is_active,
            image=image
        )
        messages.success(request, "Product added successfully.")
    return redirect('products')


def edit_product(request, product_id):
    prod = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        tag = request.POST.get('tag')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')

        if name != prod.name and Product.objects.filter(name=name).exclude(id=product_id).exists():
            messages.error(request, "A product with this name already exists.")
            return redirect('products')

        category = None
        if category_id:
            category = get_object_or_404(Category, id=category_id)

        prod.name = name
        prod.description = description
        prod.category = category
        prod.price = price
        prod.stock = stock
        prod.tag = tag
        prod.is_active = is_active

        if image:
            prod.image = image

        prod.save()
        messages.success(request, "Product updated successfully.")

    return redirect('products')


def delete_product(request, product_id):
    prod = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        prod.delete()
        messages.success(request, "Product deleted successfully.")
    return redirect('products')


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, 
        is_active=True
    ).exclude(id=product.id).distinct()[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)

def quick_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    return render(request, 'store/quick_view.html', {'product': product})


def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Get or create session key
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
    # Check if product is already in wishlist
    if Wishlist.objects.filter(session_key=session_key, product=product).exists():
        messages.info(request, 'Product is already in your wishlist')
    else:
        # Add to wishlist
        Wishlist.objects.create(session_key=session_key, product=product)
        messages.success(request, 'Product added to wishlist successfully')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Get session key
    session_key = request.session.session_key
    
    # Remove from wishlist
    Wishlist.objects.filter(session_key=session_key, product=product).delete()
    messages.success(request, 'Product removed from wishlist')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def view_wishlist(request):
    # Get session key
    session_key = request.session.session_key
    
    # Get wishlist items
    wishlist_items = Wishlist.objects.filter(session_key=session_key).select_related('product')
    
    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'products/wishlist.html', context)


