# Nginx Reverse Proxy

Syncora should run behind Nginx or an equivalent platform router in production.

## Included Template

The repository includes:

```text
deploy/nginx/syncora.conf
```

Copy it to the server's Nginx sites directory and replace:

```text
api.syncora.example.com
```

with the real API domain.

## Reverse Proxy Flow

```text
Internet
  -> Nginx
  -> Daphne on 127.0.0.1:8000
  -> Django REST Framework and Channels
```

## REST Proxy

REST, admin, schema, Swagger, and Redoc routes are proxied to Daphne:

```text
/api/
/admin/
```

## WebSocket Proxy

WebSockets require upgrade headers:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

Without these headers, normal REST requests may work while realtime WebSocket connections fail.

## Static And Media

Nginx can serve generated static files directly:

```text
/static/ -> /var/www/syncora/staticfiles/
/media/  -> /var/www/syncora/media/
```

Only serve `/media/` publicly if uploaded files are intended to be public.
