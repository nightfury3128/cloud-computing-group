# Azure App Service deployment

This document is a runbook for deploying the Flask app (`wsgi:app`) to Azure
App Service Linux, using the **existing** resource group `rg-retail-analytics`
and the **existing** Azure SQL Database `retail-analytics-db`.

> No paid resource is provisioned here yet. The user confirms the plan before
> the App Service plan is created.

## 1. Pick a plan tier

For an Azure-for-Students subscription, use **Free (F1)** or **Basic (B1)**.
`F1` is enough for the demo (1 GB RAM, no custom domain). If you need the
app to stay warm, use `B1` (~$13/mo).

Check availability for `westus`:

```bash
az appservice list-locations --sku F1 -o table
az appservice list-locations --sku B1 -o table
```

## 2. Create the App Service plan (only after approval)

```bash
# Free tier — recommended for the submission demo
az appservice plan create \
  --resource-group rg-retail-analytics \
  --name plan-retail-analytics \
  --is-linux \
  --sku F1 \
  --location westus
```

## 3. Create the Web App

```bash
az webapp create \
  --resource-group rg-retail-analytics \
  --plan plan-retail-analytics \
  --name retail-analytics-web \
  --runtime "PYTHON:3.12"
```

The `--name` has to be globally unique on `azurewebsites.net`; rename if taken.

## 4. Configure app settings (never commit secrets)

```bash
# Generate a fresh secret key for production
SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")

az webapp config appsettings set \
  --resource-group rg-retail-analytics \
  --name retail-analytics-web \
  --settings \
     SQL_SERVER=retail-sql-904734d7 \
     SQL_DB=retail-analytics-db \
     SQL_ADMIN=<application-sql-user> \
     SQL_PASSWORD=<kept-in-key-vault> \
     FLASK_SECRET_KEY="$SECRET" \
     FLASK_SESSION_COOKIE_SECURE=1 \
     SCM_DO_BUILD_DURING_DEPLOYMENT=true \
     WEBSITES_PORT=8000
```

Prefer to put `SQL_PASSWORD` in Azure Key Vault and reference it via
`@Microsoft.KeyVault(SecretUri=...)`. Do **not** reuse the `retailadmin`
account for the web app — create a minimally privileged user (step 6).

## 5. Startup command

Set the App Service "Startup Command" to:

```
bash startup.sh
```

`startup.sh` runs Gunicorn with 2 workers × 4 threads on port 8000.

## 6. Minimally privileged database user

Connect to the Azure SQL DB as `retailadmin` once (e.g. via Azure Portal
Query editor or `sqlcmd`) and run:

```sql
CREATE USER app_web WITH PASSWORD = '<strong-password>';
ALTER ROLE db_datareader ADD MEMBER app_web;
ALTER ROLE db_datawriter ADD MEMBER app_web;
-- Allow DDL only if you expect the app to migrate tables on startup;
-- if not, leave it out. The app creates dbo.app_users only when the
-- schema is missing, so grant CREATE TABLE just once if needed:
GRANT CREATE TABLE TO app_web;
```

Put `SQL_ADMIN=app_web` and the matching password in App Settings.

## 7. Firewall

Allow App Service outbound IPs to reach Azure SQL. The quickest path for
the demo is to enable **"Allow Azure services and resources to access this
server"** on the SQL Server firewall. For production, add the App Service's
outbound IP addresses explicitly:

```bash
az webapp show --resource-group rg-retail-analytics --name retail-analytics-web \
  --query outboundIpAddresses -o tsv
```

## 8. Deploy

Two options:

**Option A — ZIP from CLI (one-shot):**

```bash
zip -r app.zip . -x '.venv/*' '.git/*' '.github/*' 'data/raw/*' '.env' 'tests/*'
az webapp deploy \
  --resource-group rg-retail-analytics \
  --name retail-analytics-web \
  --type zip \
  --src-path app.zip
```

**Option B — GitHub Actions:** the included
`.github/workflows/azure-deploy.yml` deploys on pushes to `main`. Register
these GitHub Actions secrets after setting up a federated credential on
the Azure side (`az ad app federated-credential create ...`):

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

## 9. Verify

```bash
# App health
curl -i https://retail-analytics-web.azurewebsites.net/healthz
# Should return: {"ok": true}
```

Stream logs:

```bash
az webapp log tail --resource-group rg-retail-analytics --name retail-analytics-web
```

## 10. HTTPS

Azure App Service serves HTTPS on the default `*.azurewebsites.net` domain
automatically. Also redirect HTTP to HTTPS:

```bash
az webapp update \
  --resource-group rg-retail-analytics \
  --name retail-analytics-web \
  --https-only true
```

## Rollback

```bash
az webapp deployment list-publishing-profiles ...
# Previous ZIP uploads stay for 10 deployments and can be redeployed.
```
