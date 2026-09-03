# Production Verification

Use this checklist after deploying Syncora to a real HTTPS domain.

## Local Release Gates

Run these before deploying:

```bash
python manage.py check
python manage.py spectacular --validate --file schema.yml
python manage.py migrate --noinput
python manage.py test
python manage.py validate_performance --products 20 --customers 20 --sales 40 --page-size 10
```

## Live System Checks

Replace `api.syncora.example.com` with the real production domain.

### Health

```bash
curl https://api.syncora.example.com/api/health/
```

Expected:

```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Authentication

```bash
curl -X POST https://api.syncora.example.com/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"your-password"}'
```

Confirm that refresh and access tokens are returned, then call an authenticated endpoint with the access token.

### Organization And Branch

- Create an organization.
- Create at least one branch.
- Add or review memberships.
- Confirm unauthorized users cannot read the tenant.

### Inventory

- Create a category and product.
- Add inventory stock for a branch.
- Increase and decrease stock through the API.
- Confirm stock movements are recorded.

### Purchasing

- Create a supplier.
- Create a purchase order.
- Order and receive the purchase.
- Confirm inventory increases.
- Confirm supplier balance updates.

### Sales

- Create a customer.
- Create a sale with line items.
- Complete the sale.
- Add a payment.
- Confirm inventory decreases and customer balance updates.

### Finance

- Create an expense.
- Approve it with an authorized accounting/admin user.
- Confirm profit/loss and dashboard summaries reflect the change.

### Realtime

Open two authenticated clients:

```text
Client A -> performs a sale or inventory update
Client B -> connected to wss://api.syncora.example.com/ws/organizations/{organization_id}/?token={access_token}
```

Client B should receive related realtime events such as:

```text
sale.completed
inventory.updated
dashboard.updated
```

### Security Regression

Verify these fail:

- Company A user reads Company B records.
- Sales employee approves an expense.
- Branch-restricted employee reads another branch's data.
- Unauthenticated request reads protected `/api/v1/` data.

## Deployment Complete Criteria

Deployment is complete only when:

- `/api/health/` returns healthy over HTTPS.
- `/api/docs/` loads over HTTPS.
- JWT login works against production.
- Core business workflows work against production PostgreSQL.
- WebSocket clients connect over WSS.
- Cross-tenant and cross-branch access attempts fail.
- GitHub Actions test workflow passes.
- Deployment workflow completes successfully.
- A database backup exists and a restore has been tested in a non-production environment.
