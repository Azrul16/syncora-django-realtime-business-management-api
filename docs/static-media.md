# Static And Media Files

Syncora separates Django static assets from user-uploaded media.

## Static Files

Static files are generated into `staticfiles/`:

```bash
python manage.py collectstatic --noinput
```

Production reverse proxies can serve the collected directory directly:

```text
/static/ -> /var/www/syncora/staticfiles/
```

The project uses Django's manifest static files storage by default so collected assets can be cache-friendly in production.

## Media Files

User-uploaded files belong under `media/`:

```text
/media/ -> /var/www/syncora/media/
```

Future product images, company logos, receipts, and expense documents should use media storage, not static storage.

## Git Safety

Both generated directories are ignored by git:

```text
staticfiles/
media/
```

Do not commit collected assets or uploaded business files.

## Production Notes

- Run `collectstatic` during deployment after installing dependencies.
- Let Nginx or the platform serve `/static/`.
- Serve `/media/` only if uploaded files are intended to be public.
- For private documents, use protected object storage or authenticated download endpoints.
