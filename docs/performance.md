# Performance Validation

Day 9 added repeatable performance validation for the busiest API surfaces:

- `GET /api/v1/products/`
- `GET /api/v1/inventory/`
- `GET /api/v1/sales/`
- `GET /api/v1/dashboard/summary/`
- `GET /api/v1/dashboard/top-products/`

Use the benchmark command with modest local data while developing:

```bash
python manage.py validate_performance --products 100 --customers 100 --sales 200
```

The command prints CSV rows with endpoint name, HTTP status, SQL query count, response time in milliseconds, and response size in bytes. Larger PostgreSQL-backed runs can increase the same options to validate growth behavior without changing code.

The automated test suite also includes query-profile guardrails for representative list and dashboard endpoints, pagination cap checks, and integration flows for purchasing, sales, payments, finance summaries, tenant isolation, realtime emission, and transaction rollback.

Latest local validation run:

```text
python manage.py validate_performance --products 20 --customers 20 --sales 40 --page-size 10
```

| Endpoint | Status | Queries | Duration ms | Response bytes |
| --- | ---: | ---: | ---: | ---: |
| products | 200 | 2 | 166.33 | 3410 |
| inventory | 200 | 5 | 22.99 | 2114 |
| sales | 200 | 8 | 21.75 | 6250 |
| dashboard_summary | 200 | 16 | 17.84 | 237 |
| dashboard_top_products | 200 | 5 | 6.83 | 1752 |
