# Contributing

Syncora is a portfolio backend project, but contributions and review feedback are welcome.

## Local Workflow

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py test
```

## Development Guidelines

- Keep tenant isolation explicit in every queryset.
- Add permission checks for write actions.
- Use service-layer functions for inventory and business workflow side effects.
- Wrap stock, payment, and status transitions in transactions where race conditions are possible.
- Add tests for new API behavior, especially cross-tenant and cross-branch access.
- Do not commit `.env`, local database files, generated schemas, logs, or credentials.

## Before Opening A Pull Request

```bash
python manage.py check
python manage.py test
python manage.py spectacular --validate --file schema.yml
```

Remove generated local artifacts such as `schema.yml` unless the change intentionally updates a committed artifact.
