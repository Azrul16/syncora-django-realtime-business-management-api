# Syncora - Real-Time Multi-Tenant Business Management Platform

Syncora is a production-minded backend portfolio project for managing the operational core of a small or medium business. It combines tenant-isolated organizations, branch-level access, inventory, purchasing, sales, payments, expenses, realtime notifications, and analytics into one Django REST API.

## CV Description

Developed a real-time multi-tenant business management backend using Django, Django REST Framework, PostgreSQL, Django Channels and WebSockets. Implemented tenant-isolated organizations and branches, RBAC, inventory, purchasing, sales, payments, expenses, realtime notifications, business analytics and transactional stock management with database locking and atomic transactions.

## Technical Highlights

- Designed multi-tenant organization and branch architecture with role-based and object-level access control.
- Implemented transactional inventory, purchasing, and sales workflows with atomic database operations and row locking.
- Built realtime inventory, sales, payment, notification, and dashboard updates with Django Channels and WebSockets.
- Optimized ORM usage, pagination, filtering, indexing, and analytics endpoints while enforcing tenant isolation.

## Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- Django Channels
- WebSockets
- Simple JWT
- django-filter
- drf-spectacular
- Daphne

## Business Scope

Syncora models the major workflows expected in a business management API:

- Organizations, branches, users, memberships, roles, and branch assignments
- Products, categories, variants, inventory stock, and stock movements
- Suppliers, purchase orders, purchase receiving, and supplier balances
- Customers, sales orders, sale completion, payments, and customer balances
- Expense categories, expense approval, finance summaries, and profit/loss reporting
- Notifications, activity logs, audit logs, and realtime event dispatching

## API And Documentation

The project exposes a versioned REST API under `/api/v1/` and includes generated OpenAPI documentation through drf-spectacular:

- Swagger UI: `/api/docs/`
- Redoc: `/api/redoc/`
- OpenAPI schema: `/api/schema/`

Supporting documentation includes architecture diagrams, an ER diagram, setup instructions, deployment notes, performance checks, and final QA results.

## Quality And Production Readiness

- PostgreSQL-backed data model with tenant and branch ownership on business records
- JWT authentication with refresh rotation and token blacklist support
- Throttling, pagination, filtering, search, and centralized error responses
- Structured request logging with request IDs
- Audit logs for sensitive actions
- Environment-driven production security settings
- Demo data seeding command for local review
- Regression suite covering core business, security, realtime, reporting, and transactional workflows

## Demo Review Flow

1. Run migrations and seed demo data with `python manage.py seed_demo`.
2. Start the API with `python manage.py runserver`.
3. Open `/api/docs/` to explore authenticated endpoints.
4. Review dashboard, inventory, sales, purchasing, finance, notification, and audit endpoints.
5. Run `python manage.py test` and `python manage.py validate_performance` to verify quality gates.
