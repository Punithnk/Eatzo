# Production Deployment Checklist

## Configure the deployment

1. Copy `.env.example` to `.env`. Never commit `.env`.
2. Set `SECRET_KEY` to a unique random Django key and replace every example value.
3. Set `ALLOWED_HOSTS` to the deployed hostnames and `CSRF_TRUSTED_ORIGINS` to their HTTPS origins.
4. Set a strong `DB_PASSWORD`, SMTP credentials, and live Razorpay credentials. Keep these in the deployment secret store where available.
5. Configure a trusted HTTPS-terminating proxy in front of the Compose Nginx service. Restrict direct access to the origin. Only then set `TRUST_X_FORWARDED_PROTO=True` and `SECURE_SSL_REDIRECT=True`.
6. After HTTPS is confirmed, set `SECURE_HSTS_SECONDS` to a carefully chosen value. Enable subdomains or preload only if every affected hostname is permanently HTTPS.

## Build and start with Docker Compose

From this directory, after configuring `.env`:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose run --rm web python manage.py check --deploy
docker compose run --rm web python manage.py migrate --noinput
docker compose up -d
```

Create an administrator account when needed:

```powershell
docker compose run --rm web python manage.py createsuperuser
```

The app uses PostgreSQL in Compose. The database has a health check, and the web service waits for it. Static files are collected during the image build and shared with Nginx; uploaded media and database data use persistent volumes.

## Validate before release

- Run `python manage.py test delivery`.
- Run `python manage.py check --deploy` with the actual production environment.
- Confirm database migrations complete and backups are configured.
- Verify sign-in, checkout, payment signature/webhook handling, SMTP delivery, static assets, and media uploads.
- Confirm HTTPS redirection, secure cookies, host validation, monitoring, and log collection at the edge.

The included Nginx container listens on HTTP and is not itself a TLS endpoint. Do not expose it directly to the public internet as a production deployment; place it behind a trusted HTTPS-terminating proxy or provide a separately managed TLS configuration. Do not enable forwarded-protocol trust unless direct origin access is blocked.
