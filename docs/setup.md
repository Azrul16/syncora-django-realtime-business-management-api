# Local Setup Guide

## Environment

Copy `.env.example` to `.env` and update values for your machine. Never commit `.env`.

Minimum local variables:

```env
SECRET_KEY=your-local-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=syncora
DB_USER=syncora_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

Optional local API testing shortcut:

```env
DISABLE_AUTH_FOR_LOCAL_DEV=True
LOCAL_DEV_AUTH_EMAIL=owner@demo.syncora.local
```

Set `DISABLE_AUTH_FOR_LOCAL_DEV=False` before testing production-style authentication.

## Database

```sql
CREATE DATABASE syncora;
CREATE USER syncora_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE syncora TO syncora_user;
```

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

## Verify

```bash
python manage.py check
python manage.py test
python manage.py spectacular --validate --file schema.yml
python manage.py validate_performance --products 100 --customers 100 --sales 200
```

`schema.yml` is a generated local artifact and does not need to be committed unless you intentionally publish a static schema snapshot.
