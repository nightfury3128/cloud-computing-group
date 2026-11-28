# Member A — Cloud & Web Application

## 1. Cloud architecture

The retail-analytics system runs on two Azure services, both inside the
existing resource group `rg-retail-analytics` (region `westus`):

1. **Azure SQL Database** (`retail-analytics-db`, free-limit + AutoPause)
   stores the three source tables (`households`, `products`,
   `transactions`) and one application-managed table (`app_users`).
2. **Azure App Service (Linux, Python 3.12)** hosts the Flask web app.
   The platform terminates TLS and forwards requests to Gunicorn on
   port 8000 via `startup.sh`.

The web app signs in to Azure SQL as a minimally privileged user
(`app_web`, `db_datareader` + `db_datawriter`). Secrets live in App
Service settings (and should migrate to Key Vault for the final
submission). `retailadmin` is only used for one-off DDL and is never
embedded in the web app.

Data flow for the three primary user actions is summarised in
`docs/ARCHITECTURE.md`. In short, every page loads a request-scoped
`mssql_python` connection, issues parameterised SQL, and releases the
connection in Flask's teardown callback. There is no ORM: queries are
hand-written to match the assignment's join and sort order
(`HSHD_NUM → BASKET_NUM → DATE → PRODUCT_NUM → DEPARTMENT → COMMODITY`).

Observability:

- `/healthz` runs `SELECT 1` against Azure SQL and returns JSON.
- App Service stdout/stderr is streamed with `az webapp log tail`.
- Azure SQL's free-tier logs are accessible from the portal.

## 2. Web application

The Flask app is organised around four blueprints:

| Blueprint | Routes | Purpose |
|---|---|---|
| `auth` | `/register`, `/login`, `/logout` | Registration with validation, scrypt-hashed passwords, session cookies |
| `dashboard` | `/dashboard` | KPIs + three Chart.js panels (by year, by department, monthly trend) |
| `household` | `/household`, `/household/<n>`, `/household/search`, `/household/suggest` | Search by HSHD_NUM, 50-row paginated transaction grid, per-household demographics, trend, department/commodity breakdowns, brand mix, private-label savings estimate, and integration slots for churn / CLV / recommendations |
| `upload` | `/upload` | CSV upload for households / products / transactions with duplicate-aware transactional inserts |

The design system lives in a single CSS file (`app/static/css/app.css`)
with CSS variables for the palette, a sticky left sidebar, a responsive
grid, and consistent card / KPI / table / form components. Chart.js is
loaded from a public CDN with SRI.

### Household 10 verification

`/household/10` returns exactly **137** transactions. The first row
matches `data/clean/joined.csv` (`BASKET_NUM=1120, PRODUCT_NUM=6583,
DEPARTMENT=FOOD, COMMODITY=IN STORE FOOD SERVICE`). This is enforced by
`tests/test_live_queries.py::test_household_10_sort_order_matches_readme`.

### CSV upload

`app/services/csv_import.py` accepts both cleaned and raw formats (the
raw format is the one described in `analysis/clean.py`: padded headers,
`"null"` strings, zero-padded IDs, `DD-MON-YY` dates). Imports run as a
single SQL transaction; duplicate primary keys are counted and skipped
rather than failing the whole file. Newly uploaded records appear
immediately in subsequent searches because the detail page joins the
three source tables at query time.

### Security posture

- Parameterised SQL everywhere; zero string interpolation.
- `werkzeug.security.generate_password_hash` + `check_password_hash`
  (scrypt by default).
- Session cookies `HttpOnly`, `SameSite=Lax`, `Secure` in production.
- Flask's `MAX_CONTENT_LENGTH` caps upload size (default 50 MB).
- All non-auth routes are gated by `@login_required`.

### Automated tests

`pytest` suite has 24 tests across:

- CSV parser edge cases (padding, nulls, zero-padded IDs, two date formats).
- Registration validators (username rules, email, password strength).
- Route smoke tests (redirects, template render).
- Four live Azure SQL queries (household-10 count + sort, dashboard
  totals, search).

Live tests skip automatically when `SQL_SERVER` / `SQL_PASSWORD` are
unset, so CI runs the fast unit set without credentials.

## 3. Deployment

See `docs/DEPLOYMENT.md` for the full runbook. Summary:

- Plan: `F1` (free) on the Students subscription for the demo. A `B1`
  upgrade is $13/month if we need to avoid cold starts; this requires
  explicit user approval before provisioning.
- `startup.sh` runs `gunicorn wsgi:app --bind 0.0.0.0:8000`.
- `.github/workflows/azure-deploy.yml` deploys from `main` via federated
  OIDC credentials.
- The app is HTTPS-only once `az webapp update --https-only true` is
  applied.

## 4. Known follow-ups

- The App Service plan hasn't been provisioned yet — awaiting user
  confirmation on `F1` vs `B1`.
- `app_web` SQL login must be created manually once (DDL in
  `docs/DEPLOYMENT.md`).
- Analytics JSON files from Members B / C aren't present yet; the
  household detail page shows "awaiting results" cards for all three.
