# Cloud architecture (Member A)

## 1. High level

```
Browser (HTTPS)
   │
   ▼
Azure App Service (Linux, Python 3.12, Gunicorn)
   │          │
   │          └─▶ data/analytics/*.json  (ML outputs from Members B & C)
   │
   ▼
Azure SQL Database (`retail-analytics-db`)
   • households (400)
   • products   (67,284)
   • transactions (84,609)
   • app_users  (auth — app-managed)
```

Nothing else is provisioned. The App Service plan is `F1` (free) or `B1`
depending on whether the demo needs warm starts.

## 2. Request lifecycle

1. The browser hits `https://<app>.azurewebsites.net`. Azure terminates TLS.
2. App Service forwards to Gunicorn on `:8000` via the platform ingress.
3. Gunicorn hands the request to one of two worker processes (4 threads each).
4. Flask routes the URL to a blueprint:
   - `auth.*`   — register / login / logout
   - `dashboard.*` — `/dashboard` KPIs and charts
   - `household.*` — `/household`, `/household/<id>`
   - `upload.*` — CSV ingestion
5. `app/services/db.py` opens one `mssql_python` connection per request and
   closes it in a Flask `teardown_appcontext` callback.
6. All DB access goes through parameterised `?` placeholders. The join order
   and sort order for the transaction grid follows the assignment README:
   `HSHD_NUM → BASKET_NUM → DATE → PRODUCT_NUM → DEPARTMENT → COMMODITY`.

## 3. Trust & secrets

- Secrets live in App Service "Application settings" (or Key Vault refs).
  Nothing sensitive is committed; `.env` is git-ignored and `.env.example`
  is the template.
- Sessions are server-signed cookies (`SESSION_COOKIE_HTTPONLY`,
  `SAMESITE=Lax`, `SECURE=1` in production).
- Passwords are stored as `werkzeug.security` scrypt hashes.
- `retailadmin` is never used by the web app. The app signs in as
  `app_web` (minimal `db_datareader`/`db_datawriter` + `CREATE TABLE`
  for the one-off `app_users` DDL).
- SQL firewall allows Azure services + the deployment IP; App Service's
  outbound IPs can be pinned explicitly if desired.

## 4. Data flow — CSV upload (Requirement 5)

```
browser POST /upload (multipart)
   │
   ▼
app/routes/upload.py
   • validates kind + filename + size (MAX_CONTENT_LENGTH)
   • reads file bytes
   │
   ▼
app/services/csv_import.py
   • decodes UTF-8 (BOM-aware)
   • normalises headers (strip/uppercase; raw files use padded headers)
   • row by row:
       - "null"/"" → NULL
       - zero-padded IDs → int
       - "17-AUG-18" / "2018-08-17" → date
   • bulk INSERT via executemany in 500-row batches
   • dedup by PK (households/products) against existing rows
   │
   ▼
Azure SQL  (one transaction; rollback on error)
```

New uploads appear immediately in `/household/<id>` because the search page
joins the three tables at query time. `joined.csv` is only the reference
output and is never stored in the DB.

## 5. Integration with Members B & C

Members B & C publish results as JSON per household at:

- `data/analytics/churn/<HSHD_NUM>.json`
- `data/analytics/clv/<HSHD_NUM>.json`
- `data/analytics/recommendations/<HSHD_NUM>.json`

The web app reads these on demand via `app/services/analytics.py`. When a
file is missing, the household detail page shows an "awaiting results"
state — never a fabricated number. See `docs/INTEGRATION.md` for the
contract.

## 6. Observability & cost

- App Service logs (stdout/stderr) stream via `az webapp log tail`.
- `/healthz` runs `SELECT 1` against Azure SQL and returns `{"ok": true}`.
- Azure SQL is on the free-tier + AutoPause configuration. First request
  after an idle period may take a few seconds to warm up (the
  `scripts/verify_data.py` retry pattern mirrors this).

Costs incurred by this architecture, on top of the existing Azure SQL:

| Resource | Tier | Approx. monthly |
|---|---|---|
| App Service Plan | F1 (free) | $0 |
| App Service Plan | B1 (optional, warm) | ~$13 |
| GitHub Actions runner | public repo | $0 |

Nothing else is created.
