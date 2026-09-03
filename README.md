# Syncora

Real-Time Multi-Tenant Business Management Platform

## Overview

Syncora is a real-time multi-tenant business management backend designed for small and medium businesses. It provides centralized management of organizations, branches, inventory, purchases, sales, customers, suppliers, expenses, payments, analytics, notifications, and business activity while maintaining strict tenant isolation.

The project is built as a portfolio-ready Django backend that demonstrates REST API design, PostgreSQL data modeling, role-based access control, transactional business workflows, WebSocket updates, performance optimization, and production-minded configuration.

## Features

- Email-based custom user model
- Multi-tenant organizations and memberships
- Branch-level access control
- Role and permission system for owners, admins, managers, sales, inventory, accounting, and employees
- Product categories, products, variants, and inventory stock
- Purchasing workflow with order, receive, cancellation, stock increase, and activity events
- Sales workflow with confirm, complete, cancellation, payment tracking, stock deduction, and finance updates
- Expenses with approval/rejection flow and financial summaries
- Dashboard analytics for revenue, profit, inventory risk, top products, customers, suppliers, and branches
- Real-time notifications, activity logs, audit logs, and WebSocket broadcasts
- JWT authentication with refresh rotation and blacklist support
- API throttling, pagination, filtering, search, query profiling, and database indexes
- Centralized API error envelope and structured request logging

## Tech Stack

- Django
- Django REST Framework
- PostgreSQL
- Django Channels
- WebSockets
- Simple JWT
- django-filter
- drf-spectacular
- Daphne ASGI server

## Core Business Modules

- `accounts`: custom email users and authentication helpers
- `organizations`: tenants, memberships, roles, permissions, and branch access
- `branches`: tenant branches and branch-scoped operations
- `products`: categories, products, variants, pricing, and soft deletion
- `inventory`: stock records, stock movements, and transactional adjustments
- `suppliers`: supplier records and supplier analytics
- `purchases`: purchase orders, receiving, stock increases, and purchasing events
- `customers`: customer records and customer analytics
- `sales`: sales orders, completion, payments, stock deduction, and sales events
- `expenses`: expense categories, expenses, approval workflow, and finance events
- `finance`: financial summaries and dashboard analytics
- `notifications`: notifications, activity logs, audit logs, and event dispatching
- `reports`: organization dashboard summary endpoint

## Realtime Architecture

Business actions publish through a centralized event dispatcher. The dispatcher creates activity records, optional notifications, and WebSocket messages for organization, branch, module, dashboard, and user notification groups.

Architecture diagrams are available in `docs/architecture.md`.

WebSocket endpoints:

```text
ws://localhost:8000/ws/organizations/{organization_id}/?token={access_token}
ws://localhost:8000/ws/organizations/{organization_id}/inventory/?token={access_token}
ws://localhost:8000/ws/organizations/{organization_id}/purchases/?token={access_token}
ws://localhost:8000/ws/organizations/{organization_id}/sales/?token={access_token}
ws://localhost:8000/ws/organizations/{organization_id}/payments/?token={access_token}
```

## Multi-Tenant Architecture

Every major business record belongs to an organization. Branch-scoped records also belong to a branch. API querysets are scoped by active organization membership and, where applicable, branch assignments.

Tenant isolation is enforced through:

- authenticated membership checks
- object-level authorization
- branch-level query filtering
- serializer queryset restrictions
- role and permission checks
- security regression tests for cross-tenant and cross-branch access

## Security

- JWT access and refresh authentication
- Refresh-token rotation and blacklist support
- Role-based and object-level authorization
- Branch-restricted access
- API throttling for anonymous, authenticated, auth, and report traffic
- Centralized validation and API error handling
- Structured request logging with request IDs
- Append-only audit logs for sensitive actions
- Local development auth bypass controlled by environment variables

## API Documentation

Interactive API documentation is available after running the server:

```text
http://127.0.0.1:8000/api/docs/
http://127.0.0.1:8000/api/redoc/
http://127.0.0.1:8000/api/schema/
```

Main API prefix:

```text
/api/v1/
```

## Installation

```bash
git clone https://github.com/Azrul16/syncora-django-realtime-business-management-api.git
cd syncora-django-realtime-business-management-api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Create `.env` from `.env.example`:

```env
SECRET_KEY=your-local-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DISABLE_AUTH_FOR_LOCAL_DEV=False
LOCAL_DEV_AUTH_EMAIL=

DB_NAME=syncora
DB_USER=syncora_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Keep `.env` private. It is ignored by git.

More setup notes are available in `docs/setup.md`.

## Database Setup

Create the PostgreSQL database and user:

```sql
CREATE DATABASE syncora;
CREATE USER syncora_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE syncora TO syncora_user;
```

Run migrations:

```bash
python manage.py migrate
```

## Demo Data

Seed a local demo company with branches, staff, products, suppliers, customers, inventory, purchases, sales, expenses, notifications, and audit records:

```bash
python manage.py seed_demo
```

## Running The Project

```bash
python manage.py runserver
```

For ASGI/WebSocket development:

```bash
daphne config.asgi:application
```

## Running Tests

```bash
python manage.py check
python manage.py test
```

Performance validation:

```bash
python manage.py validate_performance --products 100 --customers 100 --sales 200
```

## API Examples

Get JWT tokens:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"owner@example.com\",\"password\":\"your-password\"}"
```

Create an organization:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/organizations/ ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Demo Electronics Ltd.\",\"email\":\"demo@syncora.local\"}"
```

Create a sale:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sales/ ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"branch\":1,\"customer\":1,\"items\":[{\"product\":1,\"quantity\":\"2.00\",\"unit_price\":\"100.00\"}]}"
```

Complete a sale:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sales/1/complete/ ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

View dashboard summary:

```bash
curl "http://127.0.0.1:8000/api/v1/dashboard/summary/?organization=1" ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Project Structure

```text
apps/
  accounts/
  organizations/
  branches/
  products/
  inventory/
  suppliers/
  purchases/
  customers/
  sales/
  expenses/
  finance/
  notifications/
  reports/
  core/
config/
docs/
manage.py
requirements.txt
```

## Database Schema

High-level database documentation is maintained in:

- `docs/er-diagram.md`
- `docs/portfolio.md`

## Performance

Performance notes and the benchmark command are documented in:

- `docs/performance.md`
- `docs/final-qa.md`

Deployment preparation notes are maintained in:

- `docs/deployment.md`
- `docs/asgi-deployment.md`
- `docs/postgresql-production.md`
- `docs/static-media.md`

GitHub repository metadata guidance is maintained in:

- `docs/github.md`

## Future Improvements

- Redis channel layer for multi-instance WebSocket deployment
- Docker Compose for local PostgreSQL, Redis, and Django
- CI pipeline for linting, tests, schema generation, and migrations
- Advanced PostgreSQL full-text search for large product/customer catalogs
- Export endpoints for reports and analytics
- Frontend dashboard client

## License

This project is licensed under the terms included in the [LICENSE](LICENSE) file.
