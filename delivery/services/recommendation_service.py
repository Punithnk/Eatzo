"""
Recommendation Service

Implements recommendation engine for personalized food suggestions:
- Popular items
- Recently ordered items
- Category-based recommendations
- Collaborative filtering (simple)
- Frequently bought together
- Trending restaurants
"""

from django.db.models import Count, Q, Avg, Sum
from django.contrib.auth.models import User
from collections import Counter
from ..models import (
    Item, Restaurant, Order, OrderItem, UserInteraction,
    Category
)


class RecommendationService:
    """Service for generating food recommendations."""
    
    @staticmethod
    def get_popular_items(limit=10, restaurant=None):
        """
        Get most popular items based on order frequency.
        
        Args:
            limit: Number of items to return
            restaurant: Optional restaurant filter
            
        Returns:
            QuerySet of Item instances
        """
        items = Item.objects.filter(is_available=True)
        
        if restaurant:
            items = items.filter(restaurant=restaurant)
        
        # Count orders per item
        items = items.annotate(
            order_count=Count('order_items')
        ).filter(
            order_count__gt=0
        ).order_by(
            '-order_count',
            '-restaurant__rating'
        )[:limit]
        
        return items
    
    @staticmethod
    def get_recently_ordered(user, limit=5):
        """
        Get items recently ordered by user.
        
        Args:
            user: Django User instance
            limit: Number of items to return
            
        Returns:
            QuerySet of Item instances
        """
        # Get recent orders
        recent_orders = Order.objects.filter(
            customer=user,
            status__in=['delivered', 'out_for_delivery']
        ).order_by('-created_at')[:10]
        
        # Get items from recent orders
        order_ids = [order.id for order in recent_orders]
        items = Item.objects.filter(
            order_items__order_id__in=order_ids
        ).distinct().filter(
            is_available=True
        )[:limit]
        
        return items
    
    @staticmethod
    def get_category_recommendations(user, limit=10):
        """
        Get recommendations based on user's preferred categories.
        
        Args:
            user: Django User instance
            limit: Number of items to return
            
        Returns:
            QuerySet of Item instances
        """
        # Get user's order history categories
        user_orders = Order.objects.filter(customer=user)
        order_items = OrderItem.objects.filter(
            order__in=user_orders,
            item__category__isnull=False
        ).select_related('item__category')
        
        # Count category preferences
        category_counts = Counter()
        for order_item in order_items:
            if order_item.item and order_item.item.category:
                category_counts[order_item.item.category.id] += order_item.quantity
        
        if not category_counts:
            # Fallback to popular items
            return RecommendationService.get_popular_items(limit)
        
        # Get top categories
        top_categories = [cat_id for cat_id, _ in category_counts.most_common(3)]
        
        # Get items from preferred categories
        items = Item.objects.filter(
            category_id__in=top_categories,
            is_available=True
        ).annotate(
            order_count=Count('order_items')
        ).order_by(
            '-order_count',
            '-restaurant__rating'
        )[:limit]
        
        return items
    
    @staticmethod
    def get_frequently_bought_together(item, limit=5):
        """
        Get items frequently bought together with given item.
        
        Args:
            item: Item instance
            limit: Number of items to return
            
        Returns:
            QuerySet of Item instances
        """
        # Get orders containing this item
        orders_with_item = Order.objects.filter(
            order_items__item=item
        ).values_list('id', flat=True)
        
        # Get other items in those orders
        other_items = Item.objects.filter(
            order_items__order_id__in=orders_with_item
        ).exclude(
            id=item.id
        ).annotate(
            co_occurrence=Count('order_items')
        ).filter(
            is_available=True,
            co_occurrence__gt=0
        ).order_by(
            '-co_occurrence'
        )[:limit]
        
        return other_items
    
    @staticmethod
    def get_trending_restaurants(limit=10):
        """
        Get trending restaurants based on recent orders.
        
        Args:
            limit: Number of restaurants to return
            
        Returns:
            QuerySet of Restaurant instances
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Get restaurants with orders in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        
        restaurants = Restaurant.objects.filter(
            is_active=True,
            orders__created_at__gte=week_ago
        ).annotate(
            recent_orders=Count('orders', filter=Q(orders__created_at__gte=week_ago)),
            avg_rating=Avg('rating')
        ).filter(
            recent_orders__gt=0
        ).order_by(
            '-recent_orders',
            '-avg_rating'
        )[:limit]
        
        return restaurants
    
    @staticmethod
    def get_personalized_recommendations(user, limit=20):
        """
        Get personalized recommendations combining multiple strategies.
        
        Args:
            user: Django User instance
            limit: Number of items to return
            
        Returns:
            QuerySet of Item instances
        """
        recommendations = []
        
        # Strategy 1: Recently ordered (30% weight)
        recent = list(RecommendationService.get_recently_ordered(user, limit=6))
        recommendations.extend(recent)
        
        # Strategy 2: Category-based (30% weight)
        category_based = list(RecommendationService.get_category_recommendations(user, limit=6))
        recommendations.extend(category_based)
        
        # Strategy 3: Popular items (20% weight)
        popular = list(RecommendationService.get_popular_items(limit=4))
        recommendations.extend(popular)
        
        # Strategy 4: Frequently bought together (20% weight)
        if recent:
            for item in recent[:2]:
                together = list(RecommendationService.get_frequently_bought_together(item, limit=2))
                recommendations.extend(together)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for item in recommendations:
            if item.id not in seen and item.is_available:
                seen.add(item.id)
                unique_recommendations.append(item)
        
        return unique_recommendations[:limit]
    
    @staticmethod
    def record_interaction(user, item=None, restaurant=None, interaction_type='view'):
        """
        Record user interaction for recommendation learning.
        
        Args:
            user: Django User instance
            item: Optional Item instance
            restaurant: Optional Restaurant instance
            interaction_type: Type of interaction (view, add_to_cart, order, rate)
        """
        if not item and not restaurant:
            return
        
        UserInteraction.objects.create(
            user=user,
            item=item,
            restaurant=restaurant,
            interaction_type=interaction_type
        )
    
    @staticmethod
    def get_similar_users(user, limit=10):
        """
        Find users with similar ordering patterns (for collaborative filtering).
        
        Args:
            user: Django User instance
            limit: Number of similar users to return
            
        Returns:
            QuerySet of User instances
        """
        # Get user's ordered items
        user_items = set(
            OrderItem.objects.filter(
                order__customer=user
            ).values_list('item_id', flat=True).distinct()
        )
        
        if not user_items:
            return User.objects.none()
        
        # Find users who ordered similar items
        similar_users = User.objects.filter(
            orders__order_items__item_id__in=user_items
        ).exclude(
            id=user.id
        ).annotate(
            common_items=Count('orders__order_items__item', distinct=True)
        ).filter(
            common_items__gt=0
        ).order_by(
            '-common_items'
        )[:limit]
        
        return similar_users
    
    @staticmethod
    def get_collaborative_recommendations(user, limit=10):
        """
        Get recommendations based on similar users' preferences.
        
        Args:
            user: Django User instance
            limit: Number of items to return
            
        Returns:
            QuerySet of Item instances
        """
        similar_users = RecommendationService.get_similar_users(user, limit=5)
        
        if not similar_users:
            # Fallback to popular items
            return RecommendationService.get_popular_items(limit)
        
        # Get items ordered by similar users but not by current user
        user_ordered_items = set(
            OrderItem.objects.filter(
                order__customer=user
            ).values_list('item_id', flat=True).distinct()
        )
        
        similar_user_items = Item.objects.filter(
            order_items__order__customer__in=similar_users,
            is_available=True
        ).exclude(
            id__in=user_ordered_items
        ).annotate(
            order_count=Count('order_items')
        ).filter(
            order_count__gt=0
        ).order_by(
            '-order_count',
            '-restaurant__rating'
        )[:limit]
        
        return similar_user_items
