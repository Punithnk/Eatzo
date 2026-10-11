"""
Eatzo URL Configuration

All URL patterns for the food delivery platform.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.index, name='index'),
    path('signin/', views.open_signin, name='open_signin'),
    path('signup/', views.open_signup, name='open_signup'),
    path('signin/submit/', views.signin, name='signin'),
    path('signup/submit/', views.signup, name='signup'),
    path('signout/', views.signout, name='signout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    
    # Customer Views
    path('home/', views.customer_home, name='customer_home'),
    path('menu/<int:restaurant_id>/', views.view_menu, name='view_menu'),
    path('cart/', views.show_cart, name='show_cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/create/', views.create_order, name='create_order'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Address Management
    path('addresses/', views.manage_addresses, name='manage_addresses'),
    path('address/add/', views.open_add_address, name='open_add_address'),
    path('address/create/', views.add_address, name='add_address'),
    path('address/<int:address_id>/set-default/', views.set_default_address, name='set_default_address'),
    path('address/<int:address_id>/delete/', views.delete_address, name='delete_address'),
    
    # Payment
    path('payment/<int:order_id>/create/', views.create_payment, name='create_payment'),
    path('payment/<int:order_id>/verify/', views.verify_payment, name='verify_payment'),
    path('webhook/razorpay/', views.razorpay_webhook, name='razorpay_webhook'),
    
    # Admin Views
    path('admin/dashboard/', views.admin_home, name='admin_home'),
    
    # Restaurant Owner Views
    path('restaurant/dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('restaurant/add/', views.open_add_restaurant, name='open_add_restaurant'),
    path('restaurant/create/', views.add_restaurant, name='add_restaurant'),
    path('restaurant/list/', views.open_show_restaurant, name='open_show_restaurant'),
    path('restaurant/<int:restaurant_id>/edit/', views.open_update_restaurant, name='open_update_restaurant'),
    path('restaurant/<int:restaurant_id>/update/', views.update_restaurant, name='update_restaurant'),
    path('restaurant/<int:restaurant_id>/delete/', views.delete_restaurant, name='delete_restaurant'),
    path('restaurant/<int:restaurant_id>/menu/', views.open_update_menu, name='open_update_menu'),
    path('restaurant/<int:restaurant_id>/menu/add/', views.update_menu, name='update_menu'),
    path('order/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    
    # Legacy URLs for backward compatibility (can be removed later)
    path('open_signin', views.open_signin, name='open_signin_legacy'),
    path('open_signup', views.open_signup, name='open_signup_legacy'),
    path('signup', views.signup, name='signup_legacy'),
    path('signin', views.signin, name='signin_legacy'),
]
