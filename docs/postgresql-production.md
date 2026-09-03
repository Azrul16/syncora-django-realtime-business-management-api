# Production PostgreSQL

Syncora should connect to PostgreSQL with a dedicated application user. Do not run the Django application as the `postgres` superuser.

## Create Database And User

Run the equivalent commands as a PostgreSQL administrator:

```sql
CREATE DATABASE syncora;

CREATE USER syncora_user
WITH PASSWORD 'replace-with-a-strong-password';

GRANT CONNECT ON DATABASE syncora TO syncora_user;
GRANT ALL PRIVILEGES ON DATABASE syncora TO syncora_user;
```

After connecting to the `syncora` database:

```sql
GRANT USAGE, CREATE ON SCHEMA public TO syncora_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO syncora_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO syncora_user;
```

## Environment

Use environment variables instead of committing credentials:

```env
DB_NAME=syncora
DB_USER=syncora_user
DB_PASSWORD=strong-production-password
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=60
DB_SSLMODE=require
```

Use `DB_SSLMODE=require` when PostgreSQL is reached over a network or required by the host. For a same-server Unix socket or private local network, your host may allow the value to stay empty.

## Migration Flow

After deploying code and setting the production environment:

```bash
python manage.py migrate --noinput
```

Then create the first administrative account with:

```bash
python manage.py createsuperuser
```

## Safety Notes

- Keep production credentials in `/etc/syncora/syncora.env`, platform secrets, or another protected secret store.
- Back up before major migrations.
- Test restore procedures, not only backup creation.
- Monitor connection counts and slow queries as the API grows.
