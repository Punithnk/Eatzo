"""
Payment Service

Handles payment processing including:
- Razorpay integration
- Payment verification
- Webhook handling
- Double payment prevention
- Transaction recording
"""

import razorpay
import hmac
import hashlib
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from ..models import Payment, Order


class PaymentService:
    """Service for managing payments."""
    
    @staticmethod
    def get_razorpay_client():
        """
        Get Razorpay client instance.
        
        Returns:
            razorpay.Client instance
        """
        key_id = getattr(settings, 'RAZORPAY_KEY_ID', None)
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', None)
        
        if not key_id or not key_secret:
            raise ValueError("Razorpay credentials not configured")
        
        return razorpay.Client(auth=(key_id, key_secret))
    
    @staticmethod
    @transaction.atomic
    def create_payment_intent(order):
        """
        Create Razorpay order for payment.
        
        Args:
            order: Order instance
            
        Returns:
            dict: Razorpay order data with order_id
            
        Raises:
            ValidationError: If order already has payment or is invalid
        """
        # Check if payment already exists
        if hasattr(order, 'payment'):
            if order.payment.status == 'completed':
                raise ValidationError("Order already paid")
            # Return existing payment intent
            return {
                'id': order.payment.razorpay_order_id,
                'amount': int(order.total * 100),
                'currency': 'INR'
            }
        
        # Validate order
        if order.status != 'pending':
            raise ValidationError("Can only create payment for pending orders")
        
        try:
            client = PaymentService.get_razorpay_client()
            
            # Create Razorpay order
            razorpay_order = client.order.create({
                'amount': int(order.total * 100),  # Convert to paisa
                'currency': 'INR',
                'payment_capture': 1,  # Auto-capture
                'notes': {
                    'order_id': order.id,
                    'customer_id': order.customer.id,
                }
            })
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                amount=order.total,
                status='pending',
                payment_method='razorpay',
                razorpay_order_id=razorpay_order['id']
            )
            
            return razorpay_order
            
        except Exception as e:
            raise ValidationError(f"Payment creation failed: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def verify_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify Razorpay payment signature.
        
        Args:
            razorpay_order_id: Razorpay order ID
            razorpay_payment_id: Razorpay payment ID
            razorpay_signature: Razorpay signature
            
        Returns:
            Payment instance if verified
            
        Raises:
            ValidationError: If signature is invalid or payment not found
        """
        try:
            payment = Payment.objects.select_related('order').get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            raise ValidationError("Payment not found")
        
        # Prevent double payment
        if payment.status == 'completed':
            raise ValidationError("Payment already processed")
        
        # Verify signature
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', None)
        if not key_secret:
            raise ValueError("Razorpay key secret not configured")
        
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            key_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != razorpay_signature:
            raise ValidationError("Invalid payment signature")
        
        # Update payment record
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.mark_completed()
        
        # Update order status
        if payment.order.status == 'pending':
            payment.order.update_status('confirmed', payment.order.customer)
        
        return payment
    
    @staticmethod
    def handle_webhook(payload, signature):
        """
        Handle Razorpay webhook events.
        
        Args:
            payload: Webhook payload (dict)
            signature: Webhook signature
            
        Returns:
            bool: True if webhook processed successfully
            
        Raises:
            ValidationError: If signature is invalid
        """
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', None)
        if not webhook_secret:
            # In development, skip webhook verification
            if settings.DEBUG:
                return True
            raise ValueError("Webhook secret not configured")
        
        # Verify webhook signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            str(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        if expected_signature != signature:
            raise ValidationError("Invalid webhook signature")
        
        # Handle different event types
        event = payload.get('event')
        
        if event == 'payment.captured':
            payment_id = payload.get('payload', {}).get('payment', {}).get('entity', {}).get('id')
            order_id = payload.get('payload', {}).get('payment', {}).get('entity', {}).get('notes', {}).get('order_id')
            
            if payment_id and order_id:
                try:
                    payment = Payment.objects.get(razorpay_payment_id=payment_id)
                    if payment.status != 'completed':
                        payment.mark_completed()
                        if payment.order.status == 'pending':
                            payment.order.update_status('confirmed', payment.order.customer)
                except Payment.DoesNotExist:
                    pass
        
        elif event == 'payment.failed':
            payment_id = payload.get('payload', {}).get('payment', {}).get('entity', {}).get('id')
            if payment_id:
                try:
                    payment = Payment.objects.get(razorpay_payment_id=payment_id)
                    payment.status = 'failed'
                    payment.save()
                except Payment.DoesNotExist:
                    pass
        
        return True
    
    @staticmethod
    def process_wallet_payment(order, amount):
        """
        Process wallet payment (for testing/local development).
        
        Args:
            order: Order instance
            amount: Payment amount
            
        Returns:
            Payment instance
            
        Raises:
            ValidationError: If amount doesn't match or order invalid
        """
        if amount != order.total:
            raise ValidationError("Payment amount doesn't match order total")
        
        if order.status != 'pending':
            raise ValidationError("Can only pay for pending orders")
        
        # Check if payment already exists
        if hasattr(order, 'payment'):
            if order.payment.status == 'completed':
                raise ValidationError("Order already paid")
            payment = order.payment
        else:
            payment = Payment.objects.create(
                order=order,
                amount=amount,
                status='processing',
                payment_method='wallet'
            )
        
        # Simulate payment processing
        payment.mark_completed()
        
        # Update order status
        order.update_status('confirmed', order.customer)
        
        return payment
