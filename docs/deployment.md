# Deployment Preparation

Syncora is an ASGI Django application because it serves both REST APIs and WebSockets.

## Runtime

Recommended process:

```bash
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

The repository includes a `Procfile`:

```text
web: daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
```

## Required Production Environment

```env
SECRET_KEY=long-random-production-secret
DEBUG=False
ALLOWED_HOSTS=api.example.com
CSRF_TRUSTED_ORIGINS=https://api.example.com,https://app.example.com

DB_NAME=syncora
DB_USER=syncora_user
DB_PASSWORD=strong-production-password
DB_HOST=production-postgres-host
DB_PORT=5432
DB_CONN_MAX_AGE=60
DB_SSLMODE=require

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY=same-origin
X_FRAME_OPTIONS=DENY
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=mailer@example.com
EMAIL_HOST_PASSWORD=strong-email-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

## Deployment Checklist

- Set `DEBUG=False`.
- Set a real `SECRET_KEY`.
- Restrict `ALLOWED_HOSTS`.
- Set `CSRF_TRUSTED_ORIGINS` to the HTTPS API and frontend origins.
- Keep `SECURE_PROXY_SSL_HEADER` enabled behind an HTTPS-terminating proxy.
- Configure PostgreSQL credentials from the environment.
- Use a dedicated PostgreSQL user, not the `postgres` superuser.
- Run `python manage.py migrate`.
- Run `python manage.py collectstatic --noinput`.
- Serve through HTTPS.
- Use an ASGI server such as Daphne.
- Put a reverse proxy or platform router in front of Daphne.
- Keep `.env` and production secrets out of git.

Detailed ASGI deployment notes are available in `docs/asgi-deployment.md`.
Production PostgreSQL setup notes are available in `docs/postgresql-production.md`.

## WebSocket Scaling

The project currently uses Django Channels' in-memory channel layer, which is appropriate for local development and tests.

For multi-instance production deployments, add a shared channel layer such as Redis:

```text
Internet
  -> Nginx or platform router
  -> Daphne ASGI workers
  -> Django REST and WebSockets
  -> PostgreSQL
  -> Redis channel layer
```

The business data model remains PostgreSQL-backed; Redis would only coordinate cross-process WebSocket delivery.
