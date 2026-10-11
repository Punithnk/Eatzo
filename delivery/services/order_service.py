"""
Order Service

Handles all order-related business logic including:
- Order creation
- Status updates
- Cancellation
- Price calculations with tax and delivery fees
- Edge case handling
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from ..models import (
    Order, OrderItem, Cart, CartItem, Address, Coupon,
    Payment, Restaurant, Item
)


class OrderService:
    """Service for managing orders."""
    
    # Tax rate (5% GST)
    TAX_RATE = Decimal('0.05')
    
    # Delivery fee calculation
    BASE_DELIVERY_FEE = Decimal('30.00')
    FREE_DELIVERY_THRESHOLD = Decimal('500.00')
    
    @staticmethod
    def calculate_delivery_fee(subtotal):
        """
        Calculate delivery fee based on order amount.
        
        Args:
            subtotal: Order subtotal amount
            
        Returns:
            Decimal: Delivery fee
        """
        if subtotal >= OrderService.FREE_DELIVERY_THRESHOLD:
            return Decimal('0.00')
        return OrderService.BASE_DELIVERY_FEE
    
    @staticmethod
    def calculate_tax(subtotal):
        """
        Calculate tax on order.
        
        Args:
            subtotal: Order subtotal amount
            
        Returns:
            Decimal: Tax amount
        """
        return subtotal * OrderService.TAX_RATE
    
    @staticmethod
    @transaction.atomic
    def create_order(user, delivery_address_id, coupon_code=None, customer_notes=''):
        """
        Create order from user's cart.
        This is an atomic operation to prevent race conditions.
        
        Args:
            user: Django User instance
            delivery_address_id: Address ID for delivery
            coupon_code: Optional coupon code
            customer_notes: Special instructions from customer
            
        Returns:
            Order instance
            
        Raises:
            ValidationError: If cart is empty, address invalid, or other validation fails
            Cart.DoesNotExist: If cart doesn't exist
            Address.DoesNotExist: If address doesn't exist
        """
        # Get and validate cart
        try:
            cart = Cart.objects.prefetch_related(
                'cart_items__item',
                'cart_items__item__restaurant'
            ).get(customer=user)
        except Cart.DoesNotExist:
            raise Cart.DoesNotExist("Cart not found")
        
        cart_items = cart.cart_items.all()
        
        if not cart_items.exists():
            raise ValidationError("Cart is empty")
        
        # Validate all items are still available
        for cart_item in cart_items:
            if not cart_item.item.is_available:
                raise ValidationError(
                    f"Item '{cart_item.item.name}' is no longer available"
                )
            if not cart_item.item.is_in_stock():
                raise ValidationError(
                    f"Item '{cart_item.item.name}' is out of stock"
                )
            if not cart_item.item.restaurant.is_active:
                raise ValidationError(
                    f"Restaurant '{cart_item.item.restaurant.name}' is currently closed"
                )
        
        # Get delivery address
        try:
            delivery_address = Address.objects.get(
                id=delivery_address_id,
                user=user
            )
        except Address.DoesNotExist:
            raise Address.DoesNotExist("Invalid delivery address")
        
        # Group items by restaurant (assuming one restaurant per order for simplicity)
        # In a real system, you might split orders by restaurant
        restaurants = set(item.item.restaurant for item in cart_items)
        if len(restaurants) > 1:
            raise ValidationError(
                "Cannot order from multiple restaurants in a single order. "
                "Please place separate orders."
            )
        
        restaurant = restaurants.pop()
        
        # Calculate pricing
        subtotal = sum(item.subtotal() for item in cart_items)
        
        # Apply coupon if provided
        discount = Decimal('0.00')
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                if coupon.is_valid(subtotal):
                    discount = coupon.calculate_discount(subtotal)
                    coupon.used_count += 1
                    coupon.save()
                else:
                    raise ValidationError("Invalid or expired coupon code")
            except Coupon.DoesNotExist:
                raise ValidationError("Invalid coupon code")
        
        # Calculate tax and delivery fee
        tax = OrderService.calculate_tax(subtotal)
        delivery_fee = OrderService.calculate_delivery_fee(subtotal)
        
        # Calculate total
        total = subtotal + tax + delivery_fee - discount
        
        # Validate minimum order
        if restaurant.minimum_order > 0 and subtotal < restaurant.minimum_order:
            raise ValidationError(
                f"Minimum order for {restaurant.name} is ₹{restaurant.minimum_order}"
            )
        
        # Create order
        estimated_delivery = timezone.now() + timedelta(
            minutes=restaurant.estimated_delivery_time
        )
        
        order = Order.objects.create(
            customer=user,
            restaurant=restaurant,
            delivery_address=delivery_address,
            status='pending',
            subtotal=subtotal,
            tax=tax,
            delivery_fee=delivery_fee,
            discount=discount,
            total=total,
            coupon=coupon,
            estimated_delivery_time=estimated_delivery,
            customer_notes=customer_notes
        )
        
        # Create order items (snapshot of item details)
        order_items = []
        for cart_item in cart_items:
            order_item = OrderItem.objects.create(
                order=order,
                item=cart_item.item,
                item_name=cart_item.item.name,
                item_price=cart_item.item.price,
                quantity=cart_item.quantity
            )
            order_items.append(order_item)
            
            # Update stock if tracking enabled
            if cart_item.item.stock_quantity != -1:
                cart_item.item.stock_quantity -= cart_item.quantity
                if cart_item.item.stock_quantity < 0:
                    cart_item.item.stock_quantity = 0
                cart_item.item.save()
        
        # Clear cart after successful order creation
        cart.clear()
        
        return order
    
    @staticmethod
    def cancel_order(order, user, reason=''):
        """
        Cancel an order if allowed.
        
        Args:
            order: Order instance
            user: User requesting cancellation
            reason: Cancellation reason
            
        Returns:
            Order instance
            
        Raises:
            ValidationError: If order cannot be cancelled
            PermissionError: If user doesn't have permission
        """
        # Check permissions
        if order.customer != user and not user.profile.role in ['admin', 'restaurant_owner']:
            raise PermissionError("You don't have permission to cancel this order")
        
        if not order.can_be_cancelled():
            raise ValidationError(
                f"Order cannot be cancelled. Current status: {order.status}"
            )
        
        order.update_status('cancelled', user)
        order.cancellation_reason = reason
        order.save()
        
        # Refund payment if completed
        if hasattr(order, 'payment') and order.payment.status == 'completed':
            # In production, initiate refund through payment gateway
            order.payment.status = 'refunded'
            order.payment.save()
        
        # Restore stock
        for order_item in order.order_items.all():
            if order_item.item and order_item.item.stock_quantity != -1:
                order_item.item.stock_quantity += order_item.quantity
                order_item.item.save()
        
        return order
    
    @staticmethod
    def update_order_status(order, new_status, user):
        """
        Update order status with proper validation.
        
        Args:
            order: Order instance
            new_status: New status string
            user: User making the update
            
        Returns:
            Order instance
            
        Raises:
            ValidationError: If status transition is invalid
            PermissionError: If user doesn't have permission
        """
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status: {new_status}")
        
        # Role-based status update permissions
        user_role = user.profile.role
        
        # Status transition rules
        status_rules = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['out_for_delivery', 'cancelled'],
            'out_for_delivery': ['delivered'],
            'delivered': [],
            'cancelled': []
        }
        
        allowed_statuses = status_rules.get(order.status, [])
        if new_status not in allowed_statuses:
            raise ValidationError(
                f"Cannot change status from {order.status} to {new_status}"
            )
        
        # Permission checks
        if new_status == 'confirmed' and user_role not in ['admin', 'restaurant_owner']:
            raise PermissionError("Only restaurant owners can confirm orders")
        
        if new_status == 'preparing' and user_role not in ['admin', 'restaurant_owner']:
            raise PermissionError("Only restaurant owners can mark orders as preparing")
        
        if new_status == 'out_for_delivery' and user_role not in ['admin', 'restaurant_owner', 'delivery_partner']:
            raise PermissionError("Only restaurant owners or delivery partners can update delivery status")
        
        if new_status == 'delivered' and user_role not in ['admin', 'delivery_partner']:
            raise PermissionError("Only delivery partners can mark orders as delivered")
        
        order.update_status(new_status, user)
        return order
    
    @staticmethod
    def get_user_orders(user, status=None, limit=None):
        """
        Get orders for a user with optional filtering.
        
        Args:
            user: Django User instance
            status: Optional status filter
            limit: Optional limit on number of orders
            
        Returns:
            QuerySet of Order instances
        """
        orders = Order.objects.select_related(
            'restaurant', 'delivery_address', 'payment', 'coupon'
        ).prefetch_related(
            'order_items', 'order_items__item'
        ).filter(customer=user)
        
        if status:
            orders = orders.filter(status=status)
        
        orders = orders.order_by('-created_at')
        
        if limit:
            orders = orders[:limit]
        
        return orders
    
    @staticmethod
    def get_restaurant_orders(restaurant, status=None):
        """
        Get orders for a restaurant.
        
        Args:
            restaurant: Restaurant instance
            status: Optional status filter
            
        Returns:
            QuerySet of Order instances
        """
        orders = Order.objects.select_related(
            'customer', 'delivery_address', 'payment'
        ).prefetch_related(
            'order_items'
        ).filter(restaurant=restaurant)
        
        if status:
            orders = orders.filter(status=status)
        
        return orders.order_by('-created_at')
