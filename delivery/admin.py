"""
Django Admin Configuration for Eatzo

Custom admin interfaces for better management of the food delivery platform.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import (
    UserProfile, Address, Restaurant, Category, Item,
    Cart, CartItem, Order, OrderItem, Payment, Coupon,
    OrderReview, UserInteraction
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for user profiles."""
    list_display = ['user', 'role', 'mobile', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'mobile']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for addresses."""
    list_display = ['user', 'label', 'city', 'state', 'is_default', 'created_at']
    list_filter = ['city', 'state', 'is_default']
    search_fields = ['user__username', 'street', 'city', 'pincode']
    readonly_fields = ['created_at']


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    """Admin interface for restaurants."""
    list_display = ['name', 'owner', 'cuisine', 'rating', 'is_active', 'created_at']
    list_filter = ['is_active', 'cuisine', 'created_at']
    search_fields = ['name', 'cuisine', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'name', 'description', 'picture', 'cuisine')
        }),
        ('Settings', {
            'fields': ('rating', 'total_ratings', 'is_active', 'estimated_delivery_time', 'minimum_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for categories."""
    list_display = ['name', 'icon']
    search_fields = ['name']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin interface for menu items."""
    list_display = ['name', 'restaurant', 'category', 'price', 'is_available', 'stock_quantity']
    list_filter = ['is_available', 'vegetarian', 'category', 'restaurant']
    search_fields = ['name', 'description', 'restaurant__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('restaurant', 'category', 'name', 'description', 'picture')
        }),
        ('Pricing & Availability', {
            'fields': ('price', 'vegetarian', 'is_available', 'stock_quantity', 'preparation_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class CartItemInline(admin.TabularInline):
    """Inline admin for cart items."""
    model = CartItem
    extra = 0
    readonly_fields = ['added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin interface for shopping carts."""
    list_display = ['customer', 'item_count', 'total_price', 'updated_at']
    search_fields = ['customer__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CartItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Admin interface for coupons."""
    list_display = ['code', 'discount_type', 'discount_value', 'is_active', 'used_count', 'valid_until']
    list_filter = ['is_active', 'discount_type', 'valid_until']
    search_fields = ['code', 'description']
    readonly_fields = ['used_count', 'created_at']


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items."""
    model = OrderItem
    extra = 0
    readonly_fields = ['item_name', 'item_price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for orders."""
    list_display = ['id', 'customer', 'restaurant', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at', 'restaurant']
    search_fields = ['customer__username', 'restaurant__name', 'id']
    readonly_fields = [
        'created_at', 'confirmed_at', 'delivered_at', 'cancelled_at',
        'subtotal', 'tax', 'delivery_fee', 'discount', 'total'
    ]
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('customer', 'restaurant', 'delivery_address', 'status')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax', 'delivery_fee', 'discount', 'total', 'coupon')
        }),
        ('Delivery', {
            'fields': ('delivery_partner', 'estimated_delivery_time')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'cancellation_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'confirmed_at', 'delivered_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for payments."""
    list_display = ['id', 'order', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order__id', 'razorpay_order_id', 'razorpay_payment_id']
    readonly_fields = ['created_at', 'completed_at']


@admin.register(OrderReview)
class OrderReviewAdmin(admin.ModelAdmin):
    """Admin interface for reviews."""
    list_display = ['order', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['order__id', 'comment']
    readonly_fields = ['created_at']


@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    """Admin interface for user interactions."""
    list_display = ['user', 'interaction_type', 'item', 'restaurant', 'created_at']
    list_filter = ['interaction_type', 'created_at']
    search_fields = ['user__username', 'item__name', 'restaurant__name']
    readonly_fields = ['created_at']