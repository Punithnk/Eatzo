# Production Deployment Checklist

## Pre-Deployment

### 1. Environment Variables
- [ ] Copy `.env.example` to `.env`
- [ ] Generate a secure `SECRET_KEY`:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- [ ] Set `DEBUG=False` in `.env`
- [ ] Configure `ALLOWED_HOSTS` with your domain(s)
- [ ] Set up PostgreSQL database credentials
- [ ] Configure Razorpay production keys
- [ ] Set up email backend credentials

### 2. Database
- [ ] Set `USE_POSTGRES=True` in `.env`
- [ ] Create PostgreSQL database
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`

### 3. Static Files
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Configure static file serving (WhiteNoise or CDN)

### 4. Security
- [ ] Verify `SECRET_KEY` is set and secure
- [ ] Ensure `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up SSL/HTTPS certificate
- [ ] Review and update security settings in `settings.py`

### 5. Dependencies
- [ ] Install production dependencies: `pip install -r requirements.txt`
- [ ] Use production WSGI server (Gunicorn/uWSGI)
- [ ] Set up reverse proxy (Nginx)

## Deployment Options

### Option 1: Docker
```bash
docker-compose up --build -d
```

### Option 2: Manual Deployment
1. Set up virtual environment
2. Install dependencies
3. Configure environment variables
4. Run migrations
5. Collect static files
6. Start with Gunicorn:
   ```bash
   gunicorn --bind 0.0.0.0:8000 mealmate.wsgi:application
   ```

### Option 3: Platform Services
- **Railway**: Connect repository, set env vars, deploy
- **Render**: Create Web Service, configure build/start commands
- **Heroku**: Use Procfile with Gunicorn

## Post-Deployment

- [ ] Test all major features
- [ ] Verify payment gateway integration
- [ ] Test email functionality
- [ ] Monitor logs for errors
- [ ] Set up monitoring and alerts
- [ ] Configure backups for database
- [ ] Set up SSL certificate renewal

## Important Notes

- Never commit `.env` file to version control
- Keep `SECRET_KEY` secure and rotate periodically
- Regularly update dependencies for security patches
- Monitor application logs in production
- Set up database backups
