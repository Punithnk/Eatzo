"""
General decorators for views.
"""

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import ValidationError, PermissionDenied
import logging

logger = logging.getLogger('delivery')


def handle_exceptions(redirect_url=None, error_message="An error occurred. Please try again."):
    """
    Decorator to handle exceptions in views gracefully.
    
    Args:
        redirect_url: URL to redirect on error (default: previous page)
        error_message: Default error message to show
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except ValidationError as e:
                messages.error(request, str(e))
                logger.warning(f"Validation error in {view_func.__name__}: {str(e)}")
                if redirect_url:
                    return redirect(redirect_url)
                return redirect(request.META.get('HTTP_REFERER', '/'))
            except PermissionDenied:
                messages.error(request, "You don't have permission to perform this action.")
                logger.warning(f"Permission denied in {view_func.__name__}")
                return redirect(request.META.get('HTTP_REFERER', '/'))
            except Exception as e:
                messages.error(request, error_message)
                logger.error(f"Error in {view_func.__name__}: {str(e)}", exc_info=True)
                if redirect_url:
                    return redirect(redirect_url)
                return redirect(request.META.get('HTTP_REFERER', '/'))
        return wrapper
    return decorator
