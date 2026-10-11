"""
Security utilities for input sanitization and validation.

Provides functions to sanitize user inputs and prevent common security vulnerabilities.
"""

import re
from html import escape
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError


def sanitize_string(value, max_length=None, allow_html=False):
    """
    Sanitize string input to prevent XSS and injection attacks.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags (default: False)
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If value exceeds max_length
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Strip whitespace
    value = value.strip()
    
    # Remove HTML tags if not allowed
    if not allow_html:
        value = strip_tags(value)
        value = escape(value)
    
    # Check length
    if max_length and len(value) > max_length:
        raise ValidationError(f"Input exceeds maximum length of {max_length} characters")
    
    return value


def sanitize_email(email):
    """
    Sanitize and validate email address.
    
    Args:
        email: Email string to sanitize
        
    Returns:
        Sanitized email (lowercased)
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        raise ValidationError("Email is required")
    
    email = email.strip().lower()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format")
    
    return email


def sanitize_phone(phone):
    """
    Sanitize phone number (remove non-digits).
    
    Args:
        phone: Phone number string
        
    Returns:
        Sanitized phone number (digits only)
    """
    if not phone:
        return ''
    
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    return phone


def sanitize_url(url):
    """
    Sanitize URL to prevent malicious redirects.
    
    Args:
        url: URL string
        
    Returns:
        Sanitized URL or None if invalid
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Only allow http, https protocols
    if not url.startswith(('http://', 'https://')):
        return None
    
    return url


def validate_id(id_value, model_name="ID"):
    """
    Validate that ID is a positive integer.
    
    Args:
        id_value: ID value to validate
        model_name: Name of model for error message
        
    Returns:
        Integer ID
        
    Raises:
        ValidationError: If ID is invalid
    """
    try:
        id_int = int(id_value)
        if id_int <= 0:
            raise ValidationError(f"Invalid {model_name}: must be a positive integer")
        return id_int
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid {model_name}: must be a valid integer")
