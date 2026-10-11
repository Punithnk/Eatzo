"""
Eatzo - Food Delivery Platform Views

Refactored views using Django authentication, service layer, and proper error handling.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User as DjangoUser
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.exceptions import ValidationError
import json
import logging

from .models import (
    UserProfile, Restaurant, Item, Cart, CartItem, Order, OrderItem,
    Address, Coupon, Payment, Category, UserInteraction
)
from .services import CartService, OrderService, PaymentService, RecommendationService
from .utils import (
    role_required, customer_required, restaurant_owner_required, admin_required, 
    handle_exceptions, sanitize_string, sanitize_email, validate_id
)

logger = logging.getLogger('delivery')


# ==================== AUTHENTICATION VIEWS ====================

def index(request):
    """Homepage with restaurant listings and recommendations."""
    restaurants = Restaurant.objects.filter(is_active=True).order_by('-rating', '-total_ratings')[:12]
    
    # Get recommendations if user is logged in
    recommendations = None
    trending_restaurants = RecommendationService.get_trending_restaurants(limit=6)
    
    if request.user.is_authenticated:
        try:
            recommendations = RecommendationService.get_personalized_recommendations(
                request.user, limit=8
            )
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
    
    return render(request, 'index.html', {
        'restaurants': restaurants,
        'recommendations': recommendations,
        'trending_restaurants': trending_restaurants,
    })


def open_signin(request):
    """Display sign in page."""
    if request.user.is_authenticated:
        return redirect('customer_home')
    return render(request, 'signin.html')


def open_signup(request):
    """Display sign up page."""
    if request.user.is_authenticated:
        return redirect('customer_home')
    return render(request, 'signup.html')


@require_http_methods(["POST"])
@handle_exceptions(redirect_url='open_signin')
def signin(request):
    """Handle user sign in with Django authentication."""
    username = request.POST.get('username')
    password = request.POST.get('password')

    if not username or not password:
        messages.error(request, "Please provide both username and password.")
        return redirect('open_signin')
    
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user)
        messages.success(request, f"Welcome back, {user.username}!")
        
        # Redirect based on role
        if hasattr(user, 'profile'):
            role = user.profile.role
            if role == 'admin':
                return redirect('admin_home')
            elif role == 'restaurant_owner':
                return redirect('restaurant_dashboard')
            elif role == 'delivery_partner':
                return redirect('delivery_dashboard')
        
        return redirect('customer_home')
    else:
        messages.error(request, "Invalid username or password.")
        return redirect('open_signin')


@require_http_methods(["POST"])
@handle_exceptions(redirect_url='open_signup')
def signup(request):
    """
    Handle user registration with comprehensive validation.
    
    Validates:
    - Username uniqueness and format
    - Email uniqueness and format
    - Password strength and confirmation match
    - Terms acceptance
    """
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')
    email = request.POST.get('email', '').strip().lower()
    mobile = request.POST.get('mobile', '').strip()
    terms = request.POST.get('terms')
    role = request.POST.get('role', 'customer')  # Default to customer
    
    # Validation checks
    errors = []
    
    # Required fields
    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif not username.replace('_', '').isalnum():
        errors.append("Username can only contain letters, numbers, and underscores.")
    elif DjangoUser.objects.filter(username=username).exists():
        errors.append("Username already exists. Please choose another.")
    
    if not email:
        errors.append("Email is required.")
    elif '@' not in email or '.' not in email.split('@')[1]:
        errors.append("Please enter a valid email address.")
    elif DjangoUser.objects.filter(email=email).exists():
        errors.append("Email already registered. Please use another email.")
    
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    
    if password != confirm_password:
        errors.append("Passwords do not match.")
    
    if not terms:
        errors.append("You must agree to the Terms & Conditions.")
    
    # Return errors if any
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('open_signup')
    
    # Create user
    try:
        with transaction.atomic():
            user = DjangoUser.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Create or update profile (signal may have already created it)
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': role, 'mobile': mobile or ''}
            )
            
            # Update profile if it already existed
            if not created:
                profile.role = role
                profile.mobile = mobile or ''
                profile.save()
            
            # Create default address if provided
            address_text = request.POST.get('address', '').strip()
            if address_text:
                Address.objects.create(
                    user=user,
                    label='Home',
                    street=address_text,
                    city=request.POST.get('city', '').strip(),
                    state=request.POST.get('state', '').strip(),
                    pincode=request.POST.get('pincode', '').strip(),
                    is_default=True
                )
            
            # Auto-login after signup
            login(request, user)
            messages.success(request, f"Welcome to Eatzo, {user.username}! Your account has been created successfully.")
            
            # Redirect based on role
            if role == 'admin':
                return redirect('admin_home')
            elif role == 'restaurant_owner':
                return redirect('restaurant_dashboard')
            
            return redirect('customer_home')
            
    except Exception as e:
        logger.error(f"Error during signup: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred during registration. Please try again.")
        return redirect('open_signup')


def signout(request):
    """
    Handle user sign out with proper session cleanup.
    
    Clears session data and redirects to homepage.
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f"You have been signed out successfully. See you soon, {username}!")
    else:
        messages.info(request, "You are not currently signed in.")
    
    return redirect('index')


def forgot_password(request):
    """
    Display forgot password page.
    In production, this would send a password reset email.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, 'forgot_password.html')
        
        try:
            user = DjangoUser.objects.get(email=email)
            # In production: Send password reset email
            # For now, just show a message
            messages.info(request, f"If an account exists with {email}, a password reset link has been sent.")
            logger.info(f"Password reset requested for email: {email}")
        except DjangoUser.DoesNotExist:
            # Don't reveal if email exists for security
            messages.info(request, "If an account exists with that email, a password reset link has been sent.")
        
        return redirect('open_signin')
    
    return render(request, 'forgot_password.html')


# ==================== CUSTOMER VIEWS ====================

@customer_required
def customer_home(request):
    """Customer homepage with restaurant listings."""
    restaurants = Restaurant.objects.filter(is_active=True).order_by('-rating', '-total_ratings')
    
    # Get recommendations
    recommendations = RecommendationService.get_personalized_recommendations(
        request.user, limit=8
    )
    
    return render(request, 'customer_home.html', {
        'restaurants': restaurants,
        'recommendations': recommendations,
        'username': request.user.username,
    })


@customer_required
def view_menu(request, restaurant_id):
    """Display restaurant menu."""
    restaurant = get_object_or_404(
        Restaurant.objects.prefetch_related('items'),
        id=restaurant_id,
        is_active=True
    )
    
    items = restaurant.items.filter(is_available=True).select_related('category')
    
    # Record interaction
    RecommendationService.record_interaction(
        request.user,
        restaurant=restaurant,
        interaction_type='view'
    )
    
    return render(request, 'customer_menu.html', {
        'restaurant': restaurant,
        'itemList': items,
        'username': request.user.username,
    })


@customer_required
@require_http_methods(["POST"])
def add_to_cart(request, item_id):
    """
    Add item to cart with comprehensive validation.
    
    Edge cases handled:
    - Invalid item ID
    - Item deleted after page load
    - Item unavailable/out of stock
    - Restaurant closed
    - Invalid quantity
    - Price changes
    
    Security:
    - ID validation
    - Input sanitization
    """
    try:
        # Validate item ID
        item_id = validate_id(item_id, "Item ID")
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            messages.error(request, "Quantity must be at least 1.")
            return redirect(request.META.get('HTTP_REFERER', 'customer_home'))
        
        if quantity > 50:  # Reasonable limit
            messages.error(request, "Maximum quantity per item is 50.")
            return redirect(request.META.get('HTTP_REFERER', 'customer_home'))
        
        # Add item using service (handles all validations)
        cart_item, created = CartService.add_item(request.user, item_id, quantity)
        
        # Record interaction for recommendations
        try:
            RecommendationService.record_interaction(
                request.user,
                item=cart_item.item,
                interaction_type='add_to_cart'
            )
        except Exception as e:
            logger.warning(f"Error recording interaction: {str(e)}")
            # Don't fail cart addition if interaction recording fails
        
        if created:
            messages.success(request, f"{cart_item.item.name} added to cart!")
        else:
            messages.success(request, f"Updated quantity of {cart_item.item.name} in cart!")
        
    except ValidationError as e:
        messages.error(request, str(e))
    except Item.DoesNotExist:
        messages.error(request, "Item not found. It may have been removed.")
    except ValueError:
        messages.error(request, "Invalid quantity specified.")
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}", exc_info=True)
        messages.error(request, "Failed to add item to cart. Please try again.")
    
    return redirect(request.META.get('HTTP_REFERER', 'customer_home'))


@customer_required
def show_cart(request):
    """
    Display shopping cart with calculated totals.
    
    Edge cases handled:
    - Empty cart
    - Removed items
    - Price changes
    - Unavailable items
    """
    cart_details = CartService.get_cart_details(request.user)
    
    # Calculate totals
    subtotal = cart_details['subtotal']
    tax = OrderService.calculate_tax(subtotal)
    delivery_fee = OrderService.calculate_delivery_fee(subtotal)
    total = subtotal + tax + delivery_fee
    
    return render(request, 'cart.html', {
        'cart_items': cart_details['items'],
        'subtotal': subtotal,
        'tax': tax,
        'delivery_fee': delivery_fee,
        'total': total,
        'item_count': cart_details['item_count'],
        'is_empty': cart_details['is_empty'],
        'username': request.user.username,
    })


@customer_required
@require_http_methods(["POST"])
def update_cart_item(request, item_id):
    """
    Update cart item quantity with validation.
    
    Edge cases handled:
    - Invalid quantity
    - Item removed from cart
    - Item deleted
    - Stock insufficient
    """
    try:
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            messages.error(request, "Quantity must be at least 1.")
            return redirect('show_cart')
        
        if quantity > 50:
            messages.error(request, "Maximum quantity per item is 50.")
            return redirect('show_cart')
        
        CartService.update_item_quantity(request.user, item_id, quantity)
        messages.success(request, "Cart updated successfully!")
        
    except ValueError:
        messages.error(request, "Invalid quantity specified.")
    except ValidationError as e:
        messages.error(request, str(e))
    except CartItem.DoesNotExist:
        messages.error(request, "Item not found in cart. It may have been removed.")
    except Exception as e:
        logger.error(f"Error updating cart item: {str(e)}", exc_info=True)
        messages.error(request, "Failed to update cart. Please try again.")
    
    return redirect('show_cart')


@customer_required
@require_http_methods(["POST"])
@handle_exceptions()
def remove_cart_item(request, item_id):
    """Remove item from cart."""
    removed = CartService.remove_item(request.user, item_id)
    
    if removed:
        messages.success(request, "Item removed from cart.")
    else:
        messages.error(request, "Item not found in cart.")
    
    return redirect('show_cart')


@customer_required
def checkout(request):
    """
    Display checkout page with comprehensive validation.
    
    Validates:
    - Cart is not empty
    - All items are still available
    - User has at least one address
    - Minimum order amounts
    - Restaurant availability
    """
    # Validate cart before showing checkout
    validation = CartService.validate_cart_for_checkout(request.user)
    
    if not validation['valid']:
        for error in validation['errors']:
            messages.error(request, error)
        return redirect('show_cart')
    
    cart_details = validation['cart_details']
    
    # Get user addresses
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    # Check if user has addresses
    if not addresses.exists():
        messages.info(request, "Please add a delivery address before checkout.")
        return redirect('manage_addresses')
    
    # Get available coupons
    from django.utils import timezone
    coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_until__gte=timezone.now()
    )
    
    # Calculate totals
    subtotal = cart_details['subtotal']
    tax = OrderService.calculate_tax(subtotal)
    delivery_fee = OrderService.calculate_delivery_fee(subtotal)
    total = subtotal + tax + delivery_fee
    
    return render(request, 'checkout.html', {
        'cart_items': cart_details['items'],
        'subtotal': subtotal,
        'tax': tax,
        'delivery_fee': delivery_fee,
        'total': total,
        'addresses': addresses,
        'coupons': coupons,
        'username': request.user.username,
    })


@customer_required
@require_http_methods(["POST"])
def create_order(request):
    """
    Create order from cart with comprehensive edge case handling.
    
    Edge cases handled:
    - Empty cart
    - Double submit prevention (using session token)
    - Invalid address
    - Unavailable items
    - Price changes
    - Stock depletion
    - Network failures
    - Race conditions (atomic transactions)
    """
    # Double submit prevention
    session_key = f'order_submit_{request.user.id}'
    if request.session.get(session_key):
        messages.warning(request, "Order is already being processed. Please wait...")
        return redirect('checkout')
    
    delivery_address_id = request.POST.get('delivery_address_id')
    coupon_code = request.POST.get('coupon_code', '').strip() or None
    customer_notes = request.POST.get('customer_notes', '').strip()
    
    # Validate address
    if not delivery_address_id:
        messages.error(request, "Please select a delivery address.")
        return redirect('checkout')
    
    # Set session token to prevent double submit
    import uuid
    submit_token = str(uuid.uuid4())
    request.session[session_key] = submit_token
    request.session.modified = True
    
    try:
        # Validate cart before creating order
        cart_validation = CartService.validate_cart_for_checkout(request.user)
        if not cart_validation['valid']:
            request.session.pop(session_key, None)
            for error in cart_validation['errors']:
                messages.error(request, error)
            return redirect('checkout')
        
        # Create order (atomic transaction)
        order = OrderService.create_order(
            request.user,
            delivery_address_id,
            coupon_code,
            customer_notes
        )
        
        # Record interaction for recommendations
        try:
            for order_item in order.order_items.all():
                if order_item.item:
                    RecommendationService.record_interaction(
                        request.user,
                        item=order_item.item,
                        interaction_type='order'
                    )
        except Exception as e:
            logger.warning(f"Error recording interactions: {str(e)}")
            # Don't fail order creation if interaction recording fails
        
        # Clear submit token
        request.session.pop(session_key, None)
        
        logger.info(f"Order #{order.id} created successfully for user {request.user.username}")
        messages.success(request, f"Order #{order.id} created successfully! Proceeding to payment...")
        return redirect('order_detail', order_id=order.id)
        
    except ValidationError as e:
        request.session.pop(session_key, None)
        messages.error(request, str(e))
        logger.warning(f"Order creation validation failed: {str(e)}")
        return redirect('checkout')
    except Address.DoesNotExist:
        request.session.pop(session_key, None)
        messages.error(request, "Invalid delivery address selected.")
        return redirect('checkout')
    except Exception as e:
        request.session.pop(session_key, None)
        logger.error(f"Error creating order: {str(e)}", exc_info=True)
        messages.error(request, "Failed to create order. Please try again or contact support.")
        return redirect('checkout')


@customer_required
def order_detail(request, order_id):
    """
    Display order details with IDOR prevention.
    
    Security:
    - Only order owner can view their order
    - Admin and restaurant owners can also view (for their scope)
    - Proper error handling for invalid IDs
    - Input validation
    """
    try:
        # Validate order ID
        order_id = validate_id(order_id, "Order ID")
        
        # Get order with proper filtering to prevent IDOR
        order = Order.objects.select_related(
            'restaurant', 'delivery_address', 'payment', 'coupon', 'customer'
        ).prefetch_related('order_items', 'order_items__item').get(id=order_id)
        
        # IDOR Prevention: Check if user has permission to view this order
        user_role = request.user.profile.role if hasattr(request.user, 'profile') else 'customer'
        
        if order.customer != request.user:
            # Allow admin and restaurant owners to view orders in their scope
            if user_role == 'admin':
                pass  # Admin can view all orders
            elif user_role == 'restaurant_owner' and order.restaurant.owner == request.user:
                pass  # Restaurant owner can view their restaurant's orders
            else:
                messages.error(request, "You don't have permission to view this order.")
                logger.warning(f"IDOR attempt: User {request.user.id} tried to access order {order_id}")
                return redirect('order_history')
        
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        logger.warning(f"Order not found: {order_id} requested by user {request.user.id}")
        return redirect('order_history')
    except Exception as e:
        logger.error(f"Error fetching order: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred while loading order details.")
        return redirect('order_history')
    
    return render(request, 'order_detail.html', {
        'order': order,
        'username': request.user.username,
    })


@customer_required
def order_history(request):
    """Display user's order history."""
    status_filter = request.GET.get('status', None)
    orders = OrderService.get_user_orders(request.user, status=status_filter)
    
    return render(request, 'order_history.html', {
        'orders': orders,
        'username': request.user.username,
        'status_filter': status_filter,
    })


@customer_required
@require_http_methods(["POST"])
@handle_exceptions()
def cancel_order(request, order_id):
    """Cancel an order."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    reason = request.POST.get('reason', '').strip()
    
    try:
        OrderService.cancel_order(order, request.user, reason)
        messages.success(request, f"Order #{order.id} has been cancelled.")
    except ValidationError as e:
        messages.error(request, str(e))
    except PermissionError as e:
        messages.error(request, str(e))
    
    return redirect('order_detail', order_id=order.id)


# ==================== PAYMENT VIEWS ====================

@customer_required
@require_http_methods(["POST"])
@handle_exceptions()
def create_payment(request, order_id):
    """Create Razorpay payment intent for order."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    if order.status != 'pending':
        messages.error(request, "Order is not in pending status.")
        return redirect('order_detail', order_id=order.id)
    
    try:
        razorpay_order = PaymentService.create_payment_intent(order)
        
        return JsonResponse({
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'key_id': PaymentService.get_razorpay_client().auth[0],
        })
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@customer_required
@require_http_methods(["POST"])
@csrf_exempt  # Razorpay callback
@handle_exceptions()
def verify_payment(request, order_id):
    """Verify Razorpay payment."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')
    
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return JsonResponse({
            'success': False,
            'error': 'Missing payment parameters'
        }, status=400)
    
    try:
        payment = PaymentService.verify_payment(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature
        )
        
        messages.success(request, "Payment successful! Your order has been confirmed.")
        return redirect('order_detail', order_id=order.id)
        
    except ValidationError as e:
        messages.error(request, f"Payment verification failed: {str(e)}")
        return redirect('order_detail', order_id=order.id)


@csrf_exempt  # Webhook endpoint
@require_http_methods(["POST"])
def razorpay_webhook(request):
    """Handle Razorpay webhook events."""
    payload = json.loads(request.body)
    signature = request.headers.get('X-Razorpay-Signature', '')
    
    try:
        PaymentService.handle_webhook(payload, signature)
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse(status=400)


# ==================== ADMIN VIEWS ====================

@admin_required
def admin_home(request):
    """Admin dashboard with metrics."""
    from django.db.models import Count, Sum, Avg
    from django.utils import timezone
    from datetime import timedelta
    
    # Calculate metrics
    total_orders = Order.objects.count()
    total_revenue = Payment.objects.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    total_users = DjangoUser.objects.count()
    total_restaurants = Restaurant.objects.count()
    
    # Recent orders
    recent_orders = Order.objects.select_related(
        'customer', 'restaurant'
    ).order_by('-created_at')[:10]
    
    # Today's stats
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_revenue = Payment.objects.filter(
        status='completed',
        completed_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'admin_home.html', {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_users': total_users,
        'total_restaurants': total_restaurants,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
    })


# ==================== RESTAURANT OWNER VIEWS ====================

@restaurant_owner_required
def restaurant_dashboard(request):
    """Restaurant owner dashboard."""
    # Get restaurants owned by user
    restaurants = Restaurant.objects.filter(owner=request.user)
    
    # Get pending orders
    pending_orders = Order.objects.filter(
        restaurant__owner=request.user,
        status__in=['pending', 'confirmed']
    ).select_related('customer', 'delivery_address').prefetch_related(
        'order_items'
    ).order_by('-created_at')
    
    return render(request, 'restaurant_dashboard.html', {
        'restaurants': restaurants,
        'pending_orders': pending_orders,
    })


# ==================== ADDRESS MANAGEMENT ====================

@customer_required
def manage_addresses(request):
    """
    Display and manage user addresses.
    
    Shows all saved addresses with options to set default or delete.
    """
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    return render(request, 'manage_addresses.html', {
        'addresses': addresses,
        'username': request.user.username,
    })


@customer_required
def open_add_address(request):
    """Display add address form."""
    return render(request, 'add_address_form.html', {
        'username': request.user.username,
    })


@customer_required
@require_http_methods(["POST"])
def add_address(request):
    """
    Add new address with validation.
    
    Edge cases handled:
    - Missing required fields
    - Invalid pincode format
    - Setting default address
    """
    label = sanitize_string(request.POST.get('label', 'Home'), max_length=50)
    street = sanitize_string(request.POST.get('street', ''), max_length=200)
    city = sanitize_string(request.POST.get('city', ''), max_length=100)
    state = sanitize_string(request.POST.get('state', ''), max_length=100)
    pincode = sanitize_string(request.POST.get('pincode', ''), max_length=10)
    landmark = sanitize_string(request.POST.get('landmark', ''), max_length=200)
    is_default = request.POST.get('is_default') == 'on'
    
    # Validation
    if not all([street, city, state, pincode]):
        messages.error(request, "Please fill all required address fields (Street, City, State, Pincode).")
        return redirect('open_add_address')
    
    try:
        # If setting as default, unset other defaults
        if is_default:
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        Address.objects.create(
            user=request.user,
            label=label,
            street=street,
            city=city,
            state=state,
            pincode=pincode,
            landmark=landmark,
            is_default=is_default
        )
        
        messages.success(request, "Address added successfully!")
        return redirect('manage_addresses')
    except Exception as e:
        logger.error(f"Error adding address: {str(e)}", exc_info=True)
        messages.error(request, "Failed to add address. Please try again.")
        return redirect('open_add_address')


@customer_required
@require_http_methods(["POST"])
def set_default_address(request, address_id):
    """Set address as default."""
    try:
        address_id = validate_id(address_id, "Address ID")
        address = Address.objects.get(id=address_id, user=request.user)
        
        # Unset all other defaults
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Set this as default
        address.is_default = True
        address.save()
        
        messages.success(request, f"'{address.label}' set as default address.")
    except Address.DoesNotExist:
        messages.error(request, "Address not found.")
    except Exception as e:
        logger.error(f"Error setting default address: {str(e)}")
        messages.error(request, "Failed to set default address.")
    
    return redirect('manage_addresses')


@customer_required
@require_http_methods(["POST"])
def delete_address(request, address_id):
    """Delete an address."""
    try:
        address_id = validate_id(address_id, "Address ID")
        address = Address.objects.get(id=address_id, user=request.user)
        label = address.label
        address.delete()
        
        messages.success(request, f"Address '{label}' deleted successfully.")
    except Address.DoesNotExist:
        messages.error(request, "Address not found.")
    except Exception as e:
        logger.error(f"Error deleting address: {str(e)}")
        messages.error(request, "Failed to delete address.")
    
    return redirect('manage_addresses')


# ==================== RESTAURANT MANAGEMENT (Admin/Owner) ====================

@restaurant_owner_required
def open_add_restaurant(request):
    """Display add restaurant form."""
    return render(request, 'add_restaurant.html')


@restaurant_owner_required
@require_http_methods(["POST"])
@handle_exceptions()
def add_restaurant(request):
    """Create new restaurant."""
    name = request.POST.get('name')
    picture = request.POST.get('picture', '')
    cuisine = request.POST.get('cuisine', '')
    description = request.POST.get('description', '')
    estimated_delivery_time = int(request.POST.get('estimated_delivery_time', 30))
    minimum_order = float(request.POST.get('minimum_order', 0))
    
    if not name:
        messages.error(request, "Restaurant name is required.")
        return redirect('open_add_restaurant')
    
    # Check for duplicate name
    if Restaurant.objects.filter(name=name).exists():
        messages.error(request, "A restaurant with this name already exists.")
        return redirect('open_add_restaurant')
    
    restaurant = Restaurant.objects.create(
        owner=request.user,
        name=name,
        picture=picture,
        cuisine=cuisine,
        description=description,
        estimated_delivery_time=estimated_delivery_time,
        minimum_order=minimum_order,
        is_active=True
    )
    
    messages.success(request, f"Restaurant '{restaurant.name}' added successfully!")
    return redirect('restaurant_dashboard')


@restaurant_owner_required
def open_show_restaurant(request):
    """Display all restaurants (for admin/owner)."""
    if request.user.profile.role == 'admin':
        restaurants = Restaurant.objects.all()
    else:
        restaurants = Restaurant.objects.filter(owner=request.user)
    
    return render(request, 'show_restaurants.html', {
        'restaurantList': restaurants
    })


@restaurant_owner_required
def open_update_restaurant(request, restaurant_id):
    """Display update restaurant form."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Check ownership
    if restaurant.owner != request.user and request.user.profile.role != 'admin':
        messages.error(request, "You don't have permission to edit this restaurant.")
        return redirect('restaurant_dashboard')
    
    return render(request, 'update_restaurant.html', {
        'restaurant': restaurant
    })


@restaurant_owner_required
@require_http_methods(["POST"])
@handle_exceptions()
def update_restaurant(request, restaurant_id):
    """Update restaurant details."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Check ownership
    if restaurant.owner != request.user and request.user.profile.role != 'admin':
        messages.error(request, "You don't have permission to edit this restaurant.")
        return redirect('restaurant_dashboard')
    
    restaurant.name = request.POST.get('name', restaurant.name)
    restaurant.picture = request.POST.get('picture', restaurant.picture)
    restaurant.cuisine = request.POST.get('cuisine', restaurant.cuisine)
    restaurant.description = request.POST.get('description', restaurant.description)
    restaurant.estimated_delivery_time = int(request.POST.get('estimated_delivery_time', restaurant.estimated_delivery_time))
    restaurant.minimum_order = float(request.POST.get('minimum_order', restaurant.minimum_order))
    restaurant.is_active = request.POST.get('is_active') == 'on'

    restaurant.save()

    messages.success(request, f"Restaurant '{restaurant.name}' updated successfully!")
    return redirect('open_show_restaurant')


@restaurant_owner_required
@require_http_methods(["POST"])
@handle_exceptions()
def delete_restaurant(request, restaurant_id):
    """Delete restaurant."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Check ownership
    if restaurant.owner != request.user and request.user.profile.role != 'admin':
        messages.error(request, "You don't have permission to delete this restaurant.")
        return redirect('restaurant_dashboard')
    
    restaurant_name = restaurant.name
    restaurant.delete()

    messages.success(request, f"Restaurant '{restaurant_name}' deleted successfully!")
    return redirect('open_show_restaurant')


@restaurant_owner_required
def open_update_menu(request, restaurant_id):
    """Display menu management page."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Check ownership
    if restaurant.owner != request.user and request.user.profile.role != 'admin':
        messages.error(request, "You don't have permission to manage this restaurant's menu.")
        return redirect('restaurant_dashboard')
    
    items = restaurant.items.all().select_related('category')
    categories = Category.objects.all()
    
    return render(request, 'update_menu.html', {
        'restaurant': restaurant,
        'itemList': items,
        'categories': categories,
    })


@restaurant_owner_required
@require_http_methods(["POST"])
@handle_exceptions()
def update_menu(request, restaurant_id):
    """Add new menu item."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Check ownership
    if restaurant.owner != request.user and request.user.profile.role != 'admin':
        messages.error(request, "You don't have permission to manage this restaurant's menu.")
        return redirect('restaurant_dashboard')
    
        name = request.POST.get('name')
    description = request.POST.get('description', '')
    price = float(request.POST.get('price', 0))
    vegetarian = request.POST.get('vegetarian') == 'on'
    picture = request.POST.get('picture', '')
    category_id = request.POST.get('category_id')
    is_available = request.POST.get('is_available') != 'off'
    stock_quantity = int(request.POST.get('stock_quantity', -1))
    preparation_time = int(request.POST.get('preparation_time', 15))
    
    if not name or price <= 0:
        messages.error(request, "Item name and valid price are required.")
        return redirect('open_update_menu', restaurant_id=restaurant_id)
    
    category = None
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            pass
    
            Item.objects.create(
        restaurant=restaurant,
        category=category,
        name=name,
        description=description,
        price=price,
        vegetarian=vegetarian,
        picture=picture,
        is_available=is_available,
        stock_quantity=stock_quantity,
        preparation_time=preparation_time
    )
    
    messages.success(request, f"Menu item '{name}' added successfully!")
    return redirect('open_update_menu', restaurant_id=restaurant_id)


@restaurant_owner_required
@require_http_methods(["POST"])
@handle_exceptions()
def update_order_status(request, order_id):
    """Update order status (for restaurant owners)."""
    order = get_object_or_404(Order, id=order_id)
    
    # Check ownership
    if order.restaurant.owner != request.user and request.user.profile.role != 'admin':
        messages.error(request, "You don't have permission to update this order.")
        return redirect('restaurant_dashboard')
    
    new_status = request.POST.get('status')
    
    try:
        OrderService.update_order_status(order, new_status, request.user)
        messages.success(request, f"Order #{order.id} status updated to {new_status}.")
    except (ValidationError, PermissionError) as e:
        messages.error(request, str(e))
    
    return redirect('restaurant_dashboard')
