# CI/CD

Syncora includes two GitHub Actions workflows:

- `Backend Tests`: runs checks, migrations, schema validation, and the Django test suite.
- `Production Deploy`: deploys `main` after the backend test workflow succeeds.

## Test Workflow

The test workflow starts PostgreSQL, installs dependencies, runs migrations, validates the OpenAPI schema, and runs:

```bash
python manage.py test
```

## Deployment Workflow

The deployment workflow is intentionally driven by GitHub secrets. It performs the server-side equivalent of:

```bash
git pull --ff-only origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart syncora
```

## Required GitHub Secrets

Configure these repository secrets before enabling production deployment:

```text
PRODUCTION_HOST
PRODUCTION_USER
PRODUCTION_SSH_KEY
PRODUCTION_APP_DIR
PRODUCTION_SERVICE
```

`PRODUCTION_SSH_KEY` should be a private key for a deploy-only SSH user or a tightly scoped deploy key. Do not use a personal workstation key.

## Recommended Flow

```text
feature branch
  -> pull request
  -> Backend Tests
  -> merge to main
  -> Backend Tests on main
  -> Production Deploy
```

The deploy workflow should stay protected by branch protections and repository secrets.
