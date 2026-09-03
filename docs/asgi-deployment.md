# ASGI Deployment

Syncora must run as an ASGI application in production because the same Django project serves REST endpoints and Django Channels WebSockets.

## Runtime Command

Run Daphne behind a reverse proxy:

```bash
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

Platform hosts that read a `Procfile` can use:

```text
web: daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
```

## Request Flow

```text
Nginx or platform router
  -> Daphne ASGI server
  -> HTTP requests: Django REST Framework
  -> WebSocket requests: Django Channels
  -> PostgreSQL
```

## Verification

After deployment, verify both protocols:

```bash
curl https://api.syncora.example.com/api/health/
```

Then connect a WebSocket client to:

```text
wss://api.syncora.example.com/ws/organizations/{organization_id}/?token={access_token}
```

The REST API and WebSocket connection should use the same deployment process and the same Django settings module.

## systemd Template

A Linux service template is included at `deploy/systemd/syncora.service`. Adjust `User`, `WorkingDirectory`, `EnvironmentFile`, and virtualenv paths for the target server before installing it.
