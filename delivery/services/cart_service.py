"""
Cart Service

Handles all cart-related business logic including:
- Adding/removing items
- Quantity updates
- Price calculations
- Stock validation
- Edge case handling
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from ..models import Cart, CartItem, Item, UserProfile


class CartService:
    """Service for managing shopping carts."""
    
    @staticmethod
    def get_or_create_cart(user):
        """
        Get or create cart for a user.
        
        Args:
            user: Django User instance
            
        Returns:
            Cart instance
        """
        cart, created = Cart.objects.get_or_create(customer=user)
        return cart
    
    @staticmethod
    def add_item(user, item_id, quantity=1):
        """
        Add item to cart with quantity validation.
        
        Args:
            user: Django User instance
            item_id: Item ID to add
            quantity: Quantity to add (default: 1)
            
        Returns:
            tuple: (CartItem instance, created boolean)
            
        Raises:
            Item.DoesNotExist: If item doesn't exist
            ValidationError: If item is unavailable or out of stock
        """
        try:
            item = Item.objects.select_related('restaurant').get(id=item_id)
        except Item.DoesNotExist:
            raise Item.DoesNotExist(f"Item with ID {item_id} does not exist")
        
        # Validate item availability
        if not item.is_available:
            raise ValidationError("This item is currently unavailable")
        
        if not item.is_in_stock():
            raise ValidationError("This item is out of stock")
        
        # Check restaurant is active
        if not item.restaurant.is_active:
            raise ValidationError("This restaurant is currently closed")
        
        cart = CartService.get_or_create_cart(user)
        
        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            item=item,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update quantity if item already in cart
            new_quantity = cart_item.quantity + quantity
            
            # Check stock limit
            if item.stock_quantity != -1 and new_quantity > item.stock_quantity:
                raise ValidationError(
                    f"Only {item.stock_quantity} items available in stock"
                )
            
            cart_item.quantity = new_quantity
            cart_item.save()
        
        return cart_item, created
    
    @staticmethod
    def update_item_quantity(user, item_id, quantity):
        """
        Update quantity of an item in cart.
        
        Args:
            user: Django User instance
            item_id: Item ID
            quantity: New quantity (must be > 0)
            
        Returns:
            CartItem instance
            
        Raises:
            CartItem.DoesNotExist: If item not in cart
            ValidationError: If quantity invalid or stock insufficient
        """
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1")
        
        cart = CartService.get_or_create_cart(user)
        
        try:
            cart_item = CartItem.objects.select_related('item').get(
                cart=cart,
                item_id=item_id
            )
        except CartItem.DoesNotExist:
            raise CartItem.DoesNotExist("Item not found in cart")
        
        # Validate item still available
        if not cart_item.item.is_available:
            raise ValidationError("This item is no longer available")
        
        # Check stock
        if cart_item.item.stock_quantity != -1 and quantity > cart_item.item.stock_quantity:
            raise ValidationError(
                f"Only {cart_item.item.stock_quantity} items available in stock"
            )
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return cart_item
    
    @staticmethod
    def remove_item(user, item_id):
        """
        Remove item from cart.
        
        Args:
            user: Django User instance
            item_id: Item ID to remove
            
        Returns:
            bool: True if item was removed, False if not found
        """
        cart = CartService.get_or_create_cart(user)
        
        try:
            cart_item = CartItem.objects.get(cart=cart, item_id=item_id)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            return False
    
    @staticmethod
    def clear_cart(user):
        """
        Clear all items from cart.
        
        Args:
            user: Django User instance
        """
        cart = CartService.get_or_create_cart(user)
        cart.clear()
    
    @staticmethod
    def get_cart_details(user):
        """
        Get cart with all items and calculated totals.
        
        Args:
            user: Django User instance
            
        Returns:
            dict: Cart details including items, subtotal, item_count
        """
        cart = CartService.get_or_create_cart(user)
        
        cart_items = CartItem.objects.select_related('item', 'item__restaurant').filter(
            cart=cart
        )
        
        # Validate all items are still available
        valid_items = []
        for cart_item in cart_items:
            if not cart_item.item.is_available or not cart_item.item.is_in_stock():
                # Remove unavailable items
                cart_item.delete()
                continue
            
            if not cart_item.item.restaurant.is_active:
                cart_item.delete()
                continue
            
            # Check if price changed (optional: could notify user)
            valid_items.append(cart_item)
        
        subtotal = sum(item.subtotal() for item in valid_items)
        item_count = sum(item.quantity for item in valid_items)
        
        return {
            'cart': cart,
            'items': valid_items,
            'subtotal': subtotal,
            'item_count': item_count,
            'is_empty': len(valid_items) == 0
        }
    
    @staticmethod
    def validate_cart_for_checkout(user):
        """
        Validate cart before checkout.
        Checks for empty cart, unavailable items, price changes, etc.
        
        Args:
            user: Django User instance
            
        Returns:
            dict: Validation result with 'valid' boolean and 'errors' list
        """
        cart_details = CartService.get_cart_details(user)
        errors = []
        
        if cart_details['is_empty']:
            errors.append("Your cart is empty")
        
        # Check minimum order per restaurant
        restaurant_totals = {}
        for cart_item in cart_details['items']:
            restaurant = cart_item.item.restaurant
            if restaurant not in restaurant_totals:
                restaurant_totals[restaurant] = Decimal('0.00')
            restaurant_totals[restaurant] += cart_item.subtotal()
        
        for restaurant, total in restaurant_totals.items():
            if restaurant.minimum_order > 0 and total < restaurant.minimum_order:
                errors.append(
                    f"Minimum order for {restaurant.name} is ₹{restaurant.minimum_order}. "
                    f"Current total: ₹{total}"
                )
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'cart_details': cart_details
        }
