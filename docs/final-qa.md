# Final QA

This document records the final regression checks for the portfolio-ready Syncora API.

## Environment

- Date: 2026-09-03
- Runtime: local Django development environment
- Database: PostgreSQL
- API documentation: drf-spectacular OpenAPI schema

## Checks

| Check | Command | Result |
| --- | --- | --- |
| Django system check | `python manage.py check` | Passed, no issues |
| OpenAPI schema validation | `python manage.py spectacular --validate --file schema.yml` | Passed, no validation errors |
| Performance validation | `python manage.py validate_performance --products 20 --customers 20 --sales 40 --page-size 10` | Passed, all benchmark endpoints returned 200 |
| Full regression test suite | `python manage.py test` | Passed, 114 tests |

## Performance Snapshot

| Endpoint | Status | Queries | Duration ms | Response bytes |
| --- | ---: | ---: | ---: | ---: |
| Products list | 200 | 2 | 18.64 | 3411 |
| Inventory list | 200 | 5 | 24.64 | 2115 |
| Sales list | 200 | 8 | 24.51 | 6251 |
| Dashboard summary | 200 | 16 | 16.60 | 237 |
| Dashboard top products | 200 | 5 | 6.55 | 1752 |

## Coverage Notes

The regression suite covers the core portfolio flows:

- Authentication, tenant membership, RBAC, and object-level tenant isolation
- Organizations, branches, products, categories, suppliers, and customers
- Inventory stock adjustments, movements, and low-stock behavior
- Purchasing, purchase receiving, transactional stock increases, and supplier balances
- Sales, completion, payments, transactional stock decreases, and customer balances
- Expenses, approvals, finance reports, profit/loss summaries, and dashboard analytics
- Notifications, activity logs, audit logs, realtime event dispatching, and WebSocket consumers

Local test runs disable SSL redirects and secure cookie enforcement while preserving production security settings for normal runtime and deployment checks.
