"""
Service layer for Eatzo platform.

This package contains business logic separated from views.
Services handle complex operations, validations, and edge cases.
"""

from .cart_service import CartService
from .order_service import OrderService
from .payment_service import PaymentService
from .recommendation_service import RecommendationService

__all__ = [
    'CartService',
    'OrderService',
    'PaymentService',
    'RecommendationService',
]
