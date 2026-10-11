"""
Eatzo - Food Delivery Platform Models

This module contains all database models for the food delivery platform.
Models are designed with proper relationships, constraints, and business logic.
"""

from django.db import models
from django.contrib.auth.models import User as DjangoUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class UserProfile(models.Model):
    """
    Extended user profile linked to Django's User model.
    Stores additional customer information.
    """
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('restaurant_owner', 'Restaurant Owner'),
        ('delivery_partner', 'Delivery Partner'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    mobile = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Address(models.Model):
    """
    Customer delivery addresses.
    Supports multiple addresses per user.
    """
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, help_text="e.g., Home, Office")
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    landmark = models.CharField(max_length=200, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.label} - {self.user.username}"
    
    def full_address(self):
        """Returns formatted full address string."""
        parts = [self.street, self.city, self.state, self.pincode]
        if self.landmark:
            parts.insert(-1, f"Near {self.landmark}")
        return ", ".join(parts)


class Restaurant(models.Model):
    """
    Restaurant model with availability and owner management.
    """
    owner = models.ForeignKey(DjangoUser, on_delete=models.SET_NULL, null=True, related_name='owned_restaurants')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    picture = models.URLField(
        max_length=500,
        default='https://m.ahstatic.com/is/image/accorhotels/HCM_P_8147067:4by3?fmt=jpg&op_usm=1.75,0.3,2,0&resMode=sharp2&iccEmbed=true&icc=sRGB&dpr=on,1.5&wid=335&hei=251&qlt=80'
    )
    cuisine = models.CharField(max_length=200, help_text="Comma-separated cuisine types")
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    total_ratings = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, help_text="Restaurant availability")
    estimated_delivery_time = models.IntegerField(default=30, help_text="Minutes")
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-rating', '-total_ratings']
    
    def __str__(self):
        return self.name
    
    def update_rating(self, new_rating):
        """Update restaurant rating when new review is added."""
        if self.total_ratings == 0:
            self.rating = new_rating
        else:
            total = (self.rating * self.total_ratings) + new_rating
            self.total_ratings += 1
            self.rating = total / self.total_ratings
        self.save()


class Category(models.Model):
    """
    Food categories for better organization.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class or emoji")
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Item(models.Model):
    """
    Menu items with availability and stock management.
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    vegetarian = models.BooleanField(default=False)
    picture = models.URLField(
        max_length=500,
        default='https://www.indiafilings.com/learn/wp-content/uploads/2024/08/How-to-Start-Food-Business.jpg'
    )
    is_available = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=-1, help_text="-1 for unlimited stock")
    preparation_time = models.IntegerField(default=15, help_text="Minutes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['restaurant', 'is_available']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"
    
    def is_in_stock(self):
        """Check if item is available and in stock."""
        return self.is_available and (self.stock_quantity == -1 or self.stock_quantity > 0)


class CartItem(models.Model):
    """
    Cart items with quantity tracking.
    Each cart item represents one menu item with a specific quantity.
    """
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='cart_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'item']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.item.name}"
    
    def subtotal(self):
        """Calculate subtotal for this cart item."""
        return self.item.price * self.quantity


class Cart(models.Model):
    """
    Shopping cart for customers.
    One cart per customer, persists across sessions.
    """
    customer = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Cart - {self.customer.username}"
    
    def total_price(self):
        """Calculate total cart price."""
        return sum(item.subtotal() for item in self.cart_items.all())
    
    def item_count(self):
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.cart_items.all())
    
    def is_empty(self):
        """Check if cart is empty."""
        return self.cart_items.count() == 0
    
    def clear(self):
        """Clear all items from cart."""
        self.cart_items.all().delete()


class Coupon(models.Model):
    """
    Discount coupons for orders.
    """
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(
        max_length=10,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        default='percentage'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit = models.IntegerField(default=-1, help_text="-1 for unlimited")
    used_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}%"
    
    def is_valid(self, order_amount=None):
        """Check if coupon is valid for use."""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.usage_limit != -1 and self.used_count >= self.usage_limit:
            return False
        if order_amount and order_amount < self.min_order_amount:
            return False
        return True
    
    def calculate_discount(self, order_amount):
        """Calculate discount amount for given order amount."""
        if not self.is_valid(order_amount):
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = (order_amount * self.discount_value) / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = min(self.discount_value, order_amount)
        
        return discount


class Order(models.Model):
    """
    Order model with full lifecycle management.
    Status: pending → confirmed → preparing → out_for_delivery → delivered / cancelled
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='orders')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    delivery_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Coupon
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Delivery
    delivery_partner = models.ForeignKey(
        DjangoUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_orders',
        limit_choices_to={'profile__role': 'delivery_partner'}
    )
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True, help_text="Special instructions from customer")
    cancellation_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer.username} - {self.status}"
    
    def can_be_cancelled(self):
        """Check if order can still be cancelled."""
        return self.status in ['pending', 'confirmed']
    
    def update_status(self, new_status, user=None):
        """Update order status with proper timestamp tracking."""
        if new_status == 'confirmed' and self.status == 'pending':
            self.confirmed_at = timezone.now()
        elif new_status == 'delivered' and self.status != 'delivered':
            self.delivered_at = timezone.now()
        elif new_status == 'cancelled' and self.status != 'cancelled':
            self.cancelled_at = timezone.now()
        
        self.status = new_status
        self.save()


class OrderItem(models.Model):
    """
    Individual items in an order.
    Stores snapshot of item details at time of order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, related_name='order_items')
    item_name = models.CharField(max_length=100)  # Snapshot
    item_price = models.DecimalField(max_digits=10, decimal_places=2)  # Snapshot
    quantity = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.quantity}x {self.item_name} - Order #{self.order.id}"
    
    def subtotal(self):
        """Calculate subtotal for this order item."""
        return self.item_price * self.quantity


class Payment(models.Model):
    """
    Payment records linked to orders.
    Tracks payment status and transaction details.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('wallet', 'Wallet'),
        ('cod', 'Cash on Delivery'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='razorpay')
    
    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment #{self.id} - Order #{self.order.id} - {self.status}"
    
    def mark_completed(self):
        """Mark payment as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class OrderReview(models.Model):
    """
    Customer reviews for orders.
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review - Order #{self.order.id} - {self.rating} stars"


class UserInteraction(models.Model):
    """
    Tracks user interactions for recommendation system.
    Stores views, orders, ratings, etc.
    """
    INTERACTION_TYPES = [
        ('view', 'View'),
        ('add_to_cart', 'Add to Cart'),
        ('order', 'Order'),
        ('rate', 'Rate'),
    ]
    
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='interactions')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'interaction_type']),
            models.Index(fields=['item', 'interaction_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.interaction_type} - {self.item or self.restaurant}"