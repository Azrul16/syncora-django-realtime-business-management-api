# Syncora Django Realtime Business Management API

Syncora is a Django REST Framework API foundation for realtime business management workflows. It starts with accounts, organizations, organization memberships, role-based access concepts, JWT authentication, PostgreSQL settings, and Django Channels WebSocket support.

## Features

- Email-based custom user model
- Organization and membership models
- Owner, admin, manager, and employee role foundation
- Versioned REST API under `/api/v1/`
- JWT authentication endpoints
- Django Channels ASGI/WebSocket foundation
- Environment-driven PostgreSQL configuration

## Getting Started

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` file from `.env.example`, then set your database password:

```env
SECRET_KEY=your-local-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=syncora
DB_USER=syncora_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Create the PostgreSQL database and user:

```sql
CREATE DATABASE syncora;
CREATE USER syncora_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE syncora TO syncora_user;
```

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

## API

During local development, you can temporarily bypass JWT auth for REST API testing by setting:

```env
DISABLE_AUTH_FOR_LOCAL_DEV=True
LOCAL_DEV_AUTH_EMAIL=azrul@gmail.com
```

Set `DISABLE_AUTH_FOR_LOCAL_DEV=False` before enabling production-style authentication again.

- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`
- `GET /api/v1/organizations/`
- `POST /api/v1/organizations/`
- `GET /api/v1/organizations/{id}/`
- `PATCH /api/v1/organizations/{id}/`
- `GET /api/v1/organizations/{id}/members/`
- `POST /api/v1/organizations/{id}/members/`
- `PATCH /api/v1/organizations/{id}/members/{membership_id}/`
- `DELETE /api/v1/organizations/{id}/members/{membership_id}/`
- `GET /api/v1/branches/`
- `POST /api/v1/branches/`
- `GET /api/v1/products/`
- `POST /api/v1/products/`
- `GET /api/v1/categories/`
- `POST /api/v1/categories/`
- `GET /api/v1/product-variants/`
- `POST /api/v1/product-variants/`
- `GET /api/v1/inventory/`
- `POST /api/v1/inventory/`
- `POST /api/v1/inventory/{id}/increase/`
- `POST /api/v1/inventory/{id}/decrease/`
- `GET /api/v1/stock-movements/`
- `GET /api/v1/suppliers/`
- `POST /api/v1/suppliers/`
- `GET /api/v1/purchases/`
- `POST /api/v1/purchases/`
- `POST /api/v1/purchases/{id}/receive/`
- `GET /api/v1/customers/`
- `POST /api/v1/customers/`
- `GET /api/v1/sales/`
- `POST /api/v1/sales/`
- `POST /api/v1/sales/{id}/complete/`
- `GET /api/v1/expenses/`
- `POST /api/v1/expenses/`
- `GET /api/v1/organizations/{id}/dashboard/`

Organization owners and admins can manage members. Admins can manage non-owner members, while only owners can assign or change owner memberships.
Organization owners, admins, and managers can manage operational business records. Employees can read organization data but cannot create or update these records.
Inventory quantity changes go through a service layer that records stock movement history and rejects negative stock.

## WebSockets

Organization updates are exposed through:

```text
ws://localhost:8000/ws/organizations/{organization_id}/?token={access_token}
```

The token must be a valid JWT access token for a user with an active membership in the organization. On connect, the server sends:

Inventory-specific clients can also connect to:

```text
ws://localhost:8000/ws/organizations/{organization_id}/inventory/?token={access_token}
```

```json
{
  "type": "connection.ready"
}
```

When an organization is updated through the API, connected clients receive:

```json
{
  "type": "organization.updated",
  "data": {
    "id": 1,
    "name": "Example Organization"
  }
}
```

Inventory changes from completed sales are also broadcast to connected organization clients:

```json
{
  "type": "inventory.stock_updated",
  "data": {
    "id": 1,
    "branch": 1,
    "product": 1,
    "quantity": "16.00",
    "is_low_stock": false
  }
}
```

## License

This project is licensed under the terms included in the [LICENSE](LICENSE) file.
