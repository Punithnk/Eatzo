"""
Management command to seed initial data for development/testing.

Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from delivery.models import (
    UserProfile, Restaurant, Item, Category, Address, Coupon
)


class Command(BaseCommand):
    help = 'Seed database with initial data for development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        
        # Create categories
        categories = []
        category_names = ['Pizza', 'Burgers', 'Chinese', 'Indian', 'Desserts', 'Beverages']
        for name in category_names:
            category, created = Category.objects.get_or_create(name=name)
            categories.append(category)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {name}'))
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@eatzo.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            admin_user.profile.role = 'admin'
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS('Created admin user (username: admin, password: admin123)'))
        
        # Create restaurant owner
        owner_user, created = User.objects.get_or_create(
            username='owner',
            defaults={'email': 'owner@eatzo.com'}
        )
        if created:
            owner_user.set_password('owner123')
            owner_user.save()
            owner_user.profile.role = 'restaurant_owner'
            owner_user.profile.save()
            self.stdout.write(self.style.SUCCESS('Created restaurant owner (username: owner, password: owner123)'))
        
        # Create sample restaurants
        restaurants_data = [
            {
                'name': 'Pizza Palace',
                'cuisine': 'Italian, Pizza',
                'rating': 4.5,
                'description': 'Best pizza in town!',
                'estimated_delivery_time': 25,
                'minimum_order': 200.00
            },
            {
                'name': 'Burger King',
                'cuisine': 'Fast Food, Burgers',
                'rating': 4.2,
                'description': 'Juicy burgers and fries',
                'estimated_delivery_time': 20,
                'minimum_order': 150.00
            },
            {
                'name': 'Spice Garden',
                'cuisine': 'Indian, North Indian',
                'rating': 4.7,
                'description': 'Authentic Indian cuisine',
                'estimated_delivery_time': 30,
                'minimum_order': 250.00
            },
        ]
        
        for rest_data in restaurants_data:
            restaurant, created = Restaurant.objects.get_or_create(
                name=rest_data['name'],
                defaults={
                    'owner': owner_user,
                    'cuisine': rest_data['cuisine'],
                    'rating': rest_data['rating'],
                    'description': rest_data['description'],
                    'estimated_delivery_time': rest_data['estimated_delivery_time'],
                    'minimum_order': rest_data['minimum_order'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created restaurant: {restaurant.name}'))
                
                # Add sample items
                if 'Pizza' in restaurant.name:
                    items_data = [
                        {'name': 'Margherita Pizza', 'price': 299, 'category': categories[0]},
                        {'name': 'Pepperoni Pizza', 'price': 349, 'category': categories[0]},
                        {'name': 'Veggie Supreme', 'price': 399, 'category': categories[0]},
                    ]
                elif 'Burger' in restaurant.name:
                    items_data = [
                        {'name': 'Classic Burger', 'price': 199, 'category': categories[1]},
                        {'name': 'Cheese Burger', 'price': 229, 'category': categories[1]},
                        {'name': 'Chicken Burger', 'price': 249, 'category': categories[1]},
                    ]
                else:
                    items_data = [
                        {'name': 'Butter Chicken', 'price': 349, 'category': categories[3]},
                        {'name': 'Biryani', 'price': 299, 'category': categories[3]},
                        {'name': 'Paneer Tikka', 'price': 279, 'category': categories[3]},
                    ]
                
                for item_data in items_data:
                    Item.objects.create(
                        restaurant=restaurant,
                        name=item_data['name'],
                        description=f'Delicious {item_data["name"]}',
                        price=item_data['price'],
                        category=item_data['category'],
                        is_available=True,
                        vegetarian='Chicken' not in item_data['name']
                    )
        
        # Create sample coupons
        now = timezone.now()
        coupons_data = [
            {
                'code': 'WELCOME10',
                'discount_type': 'percentage',
                'discount_value': 10.00,
                'min_order_amount': 200.00,
                'valid_from': now,
                'valid_until': now + timedelta(days=365),
            },
            {
                'code': 'FLAT50',
                'discount_type': 'fixed',
                'discount_value': 50.00,
                'min_order_amount': 300.00,
                'max_discount': 50.00,
                'valid_from': now,
                'valid_until': now + timedelta(days=365),
            },
        ]
        
        for coupon_data in coupons_data:
            coupon, created = Coupon.objects.get_or_create(
                code=coupon_data['code'],
                defaults=coupon_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created coupon: {coupon.code}'))
        
        self.stdout.write(self.style.SUCCESS('\nDatabase seeding completed!'))
        self.stdout.write('\nSample credentials:')
        self.stdout.write('  Admin: username=admin, password=admin123')
        self.stdout.write('  Owner: username=owner, password=owner123')
