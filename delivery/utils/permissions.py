"""
Permission decorators for role-based access control.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    """
    Decorator to check if user has required role.
    
    Usage:
        @role_required('admin', 'restaurant_owner')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please login to access this page.")
                return redirect('open_signin')
            
            if not hasattr(request.user, 'profile'):
                messages.error(request, "User profile not found.")
                return redirect('open_signin')
            
            user_role = request.user.profile.role
            
            if user_role not in allowed_roles:
                messages.error(request, "You don't have permission to access this page.")
                raise PermissionDenied("Insufficient permissions")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def customer_required(view_func):
    """Decorator to ensure user is a customer."""
    return role_required('customer')(view_func)


def restaurant_owner_required(view_func):
    """Decorator to ensure user is a restaurant owner."""
    return role_required('restaurant_owner', 'admin')(view_func)


def admin_required(view_func):
    """Decorator to ensure user is an admin."""
    return role_required('admin')(view_func)
