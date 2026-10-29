# CANDOR EN-83 Seating Tracker

Responsive Flask application starter with seat search, status filters, edit forms, a login screen, and SQLite for local development. The original 27 seat records are seeded by `flask init-db`.

## 1. Local setup (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set a unique `SECRET_KEY` in `.env`. Load `.env` into your shell (the app intentionally does not auto-read `.env`):

```bash
set -a; source .env; set +a
flask --app app init-db
flask --app app run --debug
```

Open http://127.0.0.1:5000. The dashboard opens directly without a login screen.

## 2. Database note

SQLite is for local development only. For a multi-user AWS deployment, use PostgreSQL (for example Amazon RDS for PostgreSQL) and set `DATABASE_URL` to the connection URL. Store secrets in Elastic Beanstalk environment properties or AWS Secrets Manager, not in source control. Back up the database before schema changes.

## 3. AWS deployment outline

1. Create an AWS account and set a budget alert.
2. Create an RDS PostgreSQL database in the same VPC as the app. Keep it private; allow inbound PostgreSQL only from the Elastic Beanstalk instance security group.
3. Create an Elastic Beanstalk Python environment. Deploy this repository from its root; Elastic Beanstalk uses `requirements.txt` and the `Procfile`.
4. Configure `DATABASE_URL`, `SECRET_KEY`, and `COOKIE_SECURE=true` in the environment. Prefer Secrets Manager for production secrets.
5. Initialize the schema once using a controlled deployment/management task with the same environment variables: `flask --app app init-db`. Do not run database initialization automatically on every web-worker startup.
6. Configure HTTPS using a domain and an ACM certificate attached to an Application Load Balancer. Redirect HTTP to HTTPS.
7. Test login, seat updates from two browsers, the 18:45 reset, backups, logs, and recovery before sharing the URL.

This version intentionally has no login. Anyone who can reach the URL can view and update seating information. Do not expose it to the public internet or untrusted external users without adding an approved access-control method (such as company SSO, VPN or an identity-aware proxy), plus CSRF protection, rate limiting, secure secret storage, and database migrations.
