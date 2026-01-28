# 🍔 Eatzo - Food Delivery Platform

A production-ready, full-stack food delivery platform built with Django, inspired by Swiggy/Zomato/Uber Eats. This is a comprehensive MVP designed to showcase strong engineering fundamentals and real-world application development.

## ✨ Features

### Customer Features
- **User Authentication**: 
  - Secure signup/login with Django's authentication system
  - Forgot password flow
  - Real-time form validation
  - Auto-login after signup
  - Session persistence
- **Restaurant Browsing**: 
  - Modern card-based restaurant listings
  - Ratings, cuisine types, and delivery times
  - Responsive grid layout
- **Menu Viewing**: 
  - Beautiful restaurant headers
  - Detailed menus with images, descriptions, and prices
  - Vegetarian/Non-vegetarian badges
  - Availability indicators
- **Shopping Cart**: 
  - Persistent cart with quantity management
  - Real-time price calculations
  - Tax and delivery fee display
  - Remove/update items
- **Address Management**: 
  - Multiple delivery addresses
  - Default address selection
  - Full address management UI
- **Order Placement**: 
  - Step-by-step checkout flow
  - Address selection
  - Coupon application
  - Order summary with breakdown
  - Double-submit prevention
- **Order Tracking**: 
  - Real-time order status updates
  - Visual timeline
  - Status badges
  - Order lifecycle: pending → confirmed → preparing → out_for_delivery → delivered
- **Order History**: 
  - Filterable order list
  - Order detail views
  - Order cancellation (before preparation)
- **Coupon System**: 
  - Apply discount coupons at checkout
  - Percentage and fixed discounts
  - Minimum order validation
- **Recommendations**: 
  - Personalized food recommendations
  - Popular items
  - Recently ordered items
  - Category preferences
  - Collaborative filtering
  - Frequently bought together

### Restaurant Owner Features
- **Restaurant Management**: Create and manage restaurant profiles
- **Menu Management**: Add, update, and manage menu items
- **Order Management**: View and update order status
- **Availability Control**: Toggle restaurant and item availability
- **Stock Management**: Track item stock quantities
- **Earnings Dashboard**: View restaurant performance metrics

### Admin Features
- **Dashboard**: Comprehensive admin dashboard with metrics
- **User Management**: Manage all users and their roles
- **Restaurant Management**: Oversee all restaurants
- **Order Management**: View and manage all orders
- **Coupon Management**: Create and manage discount coupons
- **Analytics**: View platform-wide statistics

### Technical Features
- **Payment Integration**: 
  - Razorpay payment gateway integration
  - Payment verification with signature checking
  - Webhook handling
  - Double payment prevention
  - Transaction recording
- **Role-Based Access Control**: 
  - Customer, Restaurant Owner, Delivery Partner, Admin
  - Permission decorators
  - Protected routes
- **Error Handling**: 
  - Comprehensive error handling
  - User-friendly error messages
  - Toast notifications
  - Graceful error pages
- **Edge Case Handling**: 
  - Empty cart checkout prevention
  - Deleted items handling
  - Price change detection
  - Race condition prevention (atomic transactions)
  - Double submit prevention
  - Invalid ID handling
  - Stock validation
  - Network failure recovery
- **Security**: 
  - CSRF protection on all forms
  - Input sanitization and validation
  - Secure password hashing (PBKDF2)
  - IDOR prevention
  - XSS prevention
  - SQL injection prevention (Django ORM)
  - Environment variables for secrets
- **Database Optimization**: 
  - Efficient queries with select_related and prefetch_related
  - Database indexes
  - Query optimization
- **Service Layer Architecture**: 
  - Clean separation of business logic
  - 4 service classes with 28+ methods
  - Reusable business logic
- **Transaction Safety**: 
  - Atomic transactions for critical operations
  - Race condition prevention
  - Data consistency guarantees

## 🏗️ Architecture

### Clean Architecture Pattern
```
┌─────────────────────────────────────────┐
│         Templates (Presentation)         │
│  - Base template with navbar/footer      │
│  - Modern UI components                  │
│  - Responsive design                     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Views (Controllers)             │
│  - Request handling                      │
│  - Permission checks                     │
│  - Input validation                      │
│  - Error handling                        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Services (Business Logic)        │
│  - CartService                          │
│  - OrderService                         │
│  - PaymentService                       │
│  - RecommendationService               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Models (Data Layer)              │
│  - 13 comprehensive models              │
│  - Proper relationships                 │
│  - Business logic methods              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Database (PostgreSQL/SQLite)    │
│  - Optimized queries                   │
│  - Indexes                              │
│  - Transactions                         │
└─────────────────────────────────────────┘
```

### Project Structure
```
Eatzo/
├── Eatzo/
│   ├── delivery/              # Main Django app
│   │   ├── models.py          # 13 database models
│   │   ├── views.py           # 30+ view functions
│   │   ├── urls.py            # URL routing
│   │   ├── admin.py           # Django admin configuration
│   │   ├── services/          # Business logic layer
│   │   │   ├── cart_service.py
│   │   │   ├── order_service.py
│   │   │   ├── payment_service.py
│   │   │   └── recommendation_service.py
│   │   ├── utils/             # Utility functions
│   │   │   ├── permissions.py
│   │   │   ├── decorators.py
│   │   │   └── security.py    # Input sanitization
│   │   ├── templatetags/      # Custom template tags
│   │   │   └── math_filters.py
│   │   ├── Templates/         # 15+ HTML templates
│   │   │   ├── base.html     # Base template
│   │   │   ├── signin.html
│   │   │   ├── signup.html
│   │   │   ├── customer_home.html
│   │   │   ├── cart.html
│   │   │   ├── checkout.html
│   │   │   └── ...
│   │   └── static/            # CSS, JS, images
│   │       └── styles.css     # Modern styling
│   ├── mealmate/              # Django project settings
│   │   ├── settings.py        # Production-ready config
│   │   ├── urls.py            # Root URL config
│   │   └── wsgi.py            # WSGI config
│   └── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
├── UPGRADE_SUMMARY.md
└── FINAL_UPGRADE_REPORT.md
```

### Database Schema

**Core Models:**
- `UserProfile`: Extended user profiles with roles
- `Restaurant`: Restaurant information and settings
- `Item`: Menu items with availability and stock
- `Cart` / `CartItem`: Shopping cart with quantities
- `Order` / `OrderItem`: Order management with status tracking
- `Address`: Customer delivery addresses
- `Payment`: Payment records and transaction tracking
- `Coupon`: Discount coupon system
- `OrderReview`: Customer reviews and ratings
- `UserInteraction`: User behavior tracking for recommendations

### Service Layer

The application uses a service layer pattern to separate business logic from views:

- **CartService**: Handles cart operations, validation, and price calculations
- **OrderService**: Manages order creation, status updates, and cancellation
- **PaymentService**: Processes payments, verifies transactions, handles webhooks
- **RecommendationService**: Generates personalized recommendations

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL (for production) or SQLite (for development)
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Eatzo
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**
   ```bash
   cd Eatzo
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open http://127.0.0.1:8000 in your browser

### Docker Setup

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Run migrations in container**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

- `SECRET_KEY`: Django secret key (required)
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `USE_POSTGRES`: Use PostgreSQL (True/False)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Database configuration
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`: Razorpay credentials
- `EMAIL_*`: Email configuration for production

### Database Setup

**Development (SQLite):**
- No additional setup required
- Database file: `db.sqlite3`

**Production (PostgreSQL):**
1. Install PostgreSQL
2. Create database: `CREATE DATABASE eatzo;`
3. Set `USE_POSTGRES=True` in `.env`
4. Configure database credentials in `.env`

## 🧪 Testing

Run tests:
```bash
python manage.py test
```

Or with pytest:
```bash
pytest
```

## 📦 Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Configure `SECRET_KEY` (generate new one)
- [ ] Set `ALLOWED_HOSTS` with your domain
- [ ] Use PostgreSQL database
- [ ] Configure static files (WhiteNoise or S3)
- [ ] Set up media files storage (S3/Cloudinary)
- [ ] Configure email backend
- [ ] Set up SSL/HTTPS
- [ ] Configure Razorpay production keys
- [ ] Set up webhook endpoint
- [ ] Configure logging
- [ ] Set up monitoring

### Deployment Options

**Railway:**
1. Connect GitHub repository
2. Set environment variables
3. Deploy

**Render:**
1. Create new Web Service
2. Connect repository
3. Configure build and start commands
4. Set environment variables

**Heroku:**
```bash
heroku create eatzo-app
heroku addons:create heroku-postgresql
git push heroku main
heroku run python manage.py migrate
```

## 🔐 Security Features

- Password hashing with Django's PBKDF2
- CSRF protection on all forms
- SQL injection prevention (Django ORM)
- XSS protection
- Secure session management
- Role-based access control
- Input validation and sanitization
- Environment-based secret management

## 📊 API Documentation

API endpoints are available at `/api/` (if API views are implemented).

Key endpoints:
- `POST /signup/submit/` - User registration
- `POST /signin/submit/` - User login
- `GET /home/` - Customer homepage
- `GET /menu/<restaurant_id>/` - View restaurant menu
- `POST /cart/add/<item_id>/` - Add to cart
- `GET /cart/` - View cart
- `POST /order/create/` - Create order
- `POST /payment/<order_id>/create/` - Create payment
- `POST /payment/<order_id>/verify/` - Verify payment

## 🛠️ Tech Stack

- **Backend**: Django 6.0
- **Database**: PostgreSQL (production) / SQLite (development)
- **Payment**: Razorpay
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Docker, Gunicorn, Nginx
- **Static Files**: WhiteNoise

## 📝 License

This project is created for portfolio/educational purposes.

## 👤 Author

Built as a comprehensive portfolio project demonstrating full-stack development skills.

## 🙏 Acknowledgments

- Inspired by Swiggy, Zomato, and Uber Eats
- Built with Django and modern web development practices

---

**Note**: This is a portfolio project. For production use, ensure all security measures are properly configured and tested.
#   E a t z o 
 
 
