# Integration contract for Members B & C

Members B & C deliver analytical results as plain JSON files in
`data/analytics/`. The web app reads them when the user opens
`/household/<HSHD_NUM>`. If a file is missing, the page shows an
"awaiting results" state instead of fabricating a value.

Teammates can also upload results through an Azure Blob or a small
API later; right now the simplest contract is files in the repo.

## File layout

```
data/analytics/
  churn/<HSHD_NUM>.json
  clv/<HSHD_NUM>.json
  recommendations/<HSHD_NUM>.json
```

## Schemas

### Churn (`data/analytics/churn/10.json`)

```json
{
  "score": 0.72,
  "label": "high_risk",
  "as_of": "2026-11-20",
  "model": "GBDT-churn-v2",
  "features": { "recency_days": 180, "n_baskets": 4 }
}
```

- `score` — float in `[0, 1]`
- `label` — any short string, rendered verbatim
- `as_of` — ISO date
- the rest is optional

### CLV (`data/analytics/clv/10.json`)

```json
{
  "predicted_clv_usd": 1234.56,
  "horizon_months": 12,
  "model": "BG/NBD + Gamma-Gamma",
  "as_of": "2026-11-20"
}
```

### Recommendations (`data/analytics/recommendations/10.json`)

```json
{
  "items": [
    { "product_num": 163380, "label": "Grocery staple", "reason": "frequent co-purchase" },
    { "product_num": 97554,  "label": "Frozen food",    "reason": "same basket, 32% households" }
  ]
}
```

Only the first 6 items are displayed. Any extra fields are ignored.

## Private-label savings

The web app computes this from the SQL data directly (see
`households.private_label_savings`). It assumes a 22% discount for
PRIVATE vs. NATIONAL products, labelled in the UI as an "estimate".
If Member B produces a proper savings model, publish it under
`data/analytics/private_label/<HSHD_NUM>.json` and extend
`analytics.py` to read it.
