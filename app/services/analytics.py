"""Integration layer for Members B & C analytics.

Design: analytics are produced offline by teammates and written to
`data/analytics/` as JSON files, one per household, or as whole-dataset
CSVs. The web app reads from disk and returns `None` when results are
not yet available, letting the templates render an "unavailable" state
instead of fabricating numbers.

Expected files (all optional):
  data/analytics/churn/<HSHD_NUM>.json
    { "score": 0.72, "label": "high_risk", "as_of": "2026-11-20", "features": {...} }

  data/analytics/clv/<HSHD_NUM>.json
    { "predicted_clv_usd": 1234.56, "horizon_months": 12,
      "model": "BG/NBD+Gamma-Gamma", "as_of": "2026-11-20" }

  data/analytics/recommendations/<HSHD_NUM>.json
    { "items": [{ "product_num": 123, "label": "...", "reason": "basket" }, ...] }

Teammates can also drop a single CSV at data/analytics/*.csv keyed by
HSHD_NUM; the shape is small so JSON per-household is the default.
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import current_app


def _root() -> Path:
    return Path(current_app.config["PROJECT_ROOT"]) / "data" / "analytics"


def _load(kind: str, hshd_num: int) -> dict | None:
    path = _root() / kind / f"{int(hshd_num)}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        current_app.logger.warning("analytics %s/%s parse failed: %s", kind, hshd_num, e)
        return None


def load_churn(hshd_num: int) -> dict | None:
    return _load("churn", hshd_num)


def load_clv(hshd_num: int) -> dict | None:
    return _load("clv", hshd_num)


def load_recommendations(hshd_num: int) -> dict | None:
    return _load("recommendations", hshd_num)


def available_kinds() -> dict[str, int]:
    """Discovery helper for teammates to see what's been uploaded."""
    root = _root()
    out: dict[str, int] = {}
    for kind in ("churn", "clv", "recommendations"):
        d = root / kind
        out[kind] = sum(1 for _ in d.glob("*.json")) if d.exists() else 0
    return out
