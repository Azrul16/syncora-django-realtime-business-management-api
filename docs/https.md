# HTTPS And Secure WebSockets

Production Syncora traffic should use HTTPS for REST and WSS for WebSockets.

## Production URLs

```text
https://api.syncora.example.com/api/docs/
wss://api.syncora.example.com/ws/organizations/{organization_id}/?token={access_token}
```

Development can use `http://` and `ws://`, but production clients should switch to `https://` and `wss://`.

## TLS Termination

The included Nginx template terminates TLS and forwards requests to Daphne:

```text
Client
  -> HTTPS or WSS
  -> Nginx on 443
  -> Daphne on 127.0.0.1:8000
```

Django uses:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

so the application can correctly identify proxied HTTPS requests.

## Required Production Environment

```env
DEBUG=False
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
CSRF_TRUSTED_ORIGINS=https://api.syncora.example.com
```

## Certificate Notes

Use a trusted certificate provider such as Let's Encrypt or the TLS certificate system provided by your hosting platform. Keep certificate files and private keys on the server or platform, not in git.

## Verification

Verify after deployment:

```bash
curl -I https://api.syncora.example.com/api/health/
```

Then verify that a WebSocket client can connect with `wss://` and receive realtime events after a sale, inventory update, or notification event.
