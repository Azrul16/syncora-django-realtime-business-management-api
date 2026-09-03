# Backups And Health Checks

Syncora stores operational business data such as sales, payments, purchases, expenses, and inventory. Production deployments need regular PostgreSQL backups and a health endpoint for uptime checks.

## Health Check

Endpoint:

```text
GET /api/health/
```

Healthy response:

```json
{
  "status": "healthy",
  "database": "connected"
}
```

The endpoint is public so load balancers and uptime monitors can call it. It does not expose credentials, hostnames, environment values, versions, or server internals.

## PostgreSQL Backup

Example backup command:

```bash
pg_dump --format=custom --file=/var/backups/syncora/syncora-$(date +%Y%m%d-%H%M%S).dump syncora
```

Example restore command:

```bash
pg_restore --clean --if-exists --dbname=syncora /var/backups/syncora/syncora-YYYYMMDD-HHMMSS.dump
```

## Suggested Schedule

```text
Daily full backup
  -> encrypted backup storage
  -> retention policy
  -> restore test
```

## Operational Notes

- Store backups outside the application directory.
- Restrict backup file permissions.
- Encrypt off-server backups.
- Test restores on a non-production database.
- Back up before large migrations or data imports.
- Monitor `/api/health/` from outside the server network.
