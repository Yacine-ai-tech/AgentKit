"""
Insight engine — health index, risk scoring, anomalies, executive summary.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from agentkit_mcp.core.i18n import I18N, t
from agentkit_mcp.core.logger import get_logger

log = get_logger(__name__)


# ── Formatting ────────────────────────────────────────────────────────────


def format_number(value: float | None, currency: str = "$") -> str:
    """Human-readable number with automatic scale suffix."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    value = float(value)
    if abs(value) >= 1e9:
        return f"{currency}{value / 1e9:.1f}B"
    if abs(value) >= 1e6:
        return f"{currency}{value / 1e6:.1f}M"
    if abs(value) >= 1e3:
        return f"{currency}{value / 1e3:.1f}K"
    return f"{currency}{value:,.0f}"


# ── Helpers ───────────────────────────────────────────────────────────────


def _metric_lookup(df: pd.DataFrame, keywords: List[str]) -> pd.DataFrame:
    mask = df["metric"].str.lower().apply(lambda name: any(k in name for k in keywords))
    return df[mask]


# ── Key metrics ───────────────────────────────────────────────────────────


def extract_key_metrics(df: pd.DataFrame) -> Dict[str, float]:
    latest = df.sort_values("period").groupby("metric").tail(1)
    revenue = _metric_lookup(latest, ["revenue", "sales", "arr", "mrr"])
    margin = _metric_lookup(latest, ["gross margin", "margin"])
    cash = _metric_lookup(latest, ["cash", "liquidity"])
    return {
        "revenue": revenue["value"].sum() if not revenue.empty else np.nan,
        "gross_margin": margin["value"].sum() if not margin.empty else np.nan,
        "cash": cash["value"].sum() if not cash.empty else np.nan,
    }


# ── Health index ──────────────────────────────────────────────────────────


def compute_health_index(df: pd.DataFrame) -> Dict[str, float | str]:
    if df.empty:
        lbl = t("COMMON", "no_data") if I18N.lang() == "fr" else "No Data"
        return {"score": 0, "label": lbl}

    # 1. Growth calculation: isolate a single primary time series to prevent cross-metric collisions
    growth = 0.0
    for primary_metric in ["Revenue", "ARR", "MRR"]:
        rev_match = df[df["metric"].str.lower() == primary_metric.lower()].sort_values("period")
        if not rev_match.empty and len(rev_match) >= 2:
            prev = float(rev_match.iloc[-2]["value"])
            curr = float(rev_match.iloc[-1]["value"])
            if prev > 0:
                growth = (curr - prev) / prev * 100
                break
    else:
        rev = _metric_lookup(df, ["revenue", "sales", "arr", "mrr"])
        if not rev.empty:
            first_metric = rev["metric"].iloc[0]
            rev_match = rev[rev["metric"] == first_metric].sort_values("period")
            if len(rev_match) >= 2:
                prev = float(rev_match.iloc[-2]["value"])
                curr = float(rev_match.iloc[-1]["value"])
                if prev > 0:
                    growth = (curr - prev) / prev * 100

    # 2. Gross margin: 0-100% scale
    margin_s = df[df["metric"].str.lower().str.contains("gross margin|margin")]
    margin = float(margin_s["value"].mean()) if not margin_s.empty else 75.0

    # 3. Cash runway / liquidity: handle both runway in months and cash balance in USD
    cash_s = df[df["metric"].str.lower().str.contains("cash runway|runway|cash")]
    if not cash_s.empty:
        if any("month" in str(u).lower() for u in cash_s.get("unit", [])):
            runway_months = float(cash_s["value"].mean())
            cash_score = min(100.0, max(0.0, (runway_months / 24.0) * 100.0))
        else:
            cash_val = float(cash_s["value"].mean())
            cash_score = min(100.0, max(0.0, cash_val / 1_000_000 * 20.0))
    else:
        cash_score = 60.0

    # 4. Operating efficiency: 0-100 scale
    eff_s = df[df["metric"].str.lower().str.contains("operating expense|opex")]
    efficiency = max(0.0, 100.0 - min(100.0, float(eff_s["value"].mean()) / 1_000_000 * 10.0)) if not eff_s.empty else 70.0

    # Weighted composite health score (0-100)
    growth_norm = min(100.0, max(0.0, 50.0 + (growth * 5.0)))
    score = float(np.clip((0.25 * growth_norm) + (0.25 * margin) + (0.25 * cash_score) + (0.25 * efficiency), 0.0, 100.0))
    score = round(score, 1)

    labels_en = {80: "Strong", 60: "Stable", 40: "At Risk", 0: "Critical"}
    labels_fr = {80: "Solide", 60: "Stable", 40: "À risque", 0: "Critique"}
    labels = labels_fr if I18N.lang() == "fr" else labels_en
    label = next(v for k, v in sorted(labels.items(), reverse=True) if score >= k)

    return {
        "score": score,
        "label": label,
        "growth": round(float(growth), 2),
        "margin": round(float(margin), 2),
        "cash_score": round(float(cash_score), 2),
        "efficiency": round(float(efficiency), 2),
    }


# ── Anomaly detection ────────────────────────────────────────────────────


def detect_anomalies(
    df: pd.DataFrame,
    z_threshold: float = 2.5,
    method: str = "zscore",
) -> pd.DataFrame:
    """
    Advanced anomaly detection with multiple methods:
    - zscore: Statistical outliers (fast, simple)
    - iqr: Interquartile range (robust to extremes)
    - isolation_forest: Unsupervised ML (best for multivariate)
    - ewma: Exponential weighted moving average (time-series aware)
    """
    if df.empty:
        return df.copy()

    sort_col = (
        "period"
        if "period" in df.columns
        else ("month_tag" if "month_tag" in df.columns else df.columns[0])
    )
    df = df.sort_values(sort_col).copy()
    value_col = (
        "value"
        if "value" in df.columns
        else ("actual" if "actual" in df.columns else df.columns[0])
    )

    if method == "zscore":
        # Z-score based anomaly detection
        mean = df[value_col].mean()
        std = df[value_col].std() or 1
        df["z_score"] = (df[value_col] - mean) / std
        df["is_anomaly"] = df["z_score"].abs() > z_threshold

    elif method == "iqr":
        # Interquartile range method (robust to extremes)
        Q1 = df[value_col].quantile(0.25)
        Q3 = df[value_col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df["is_anomaly"] = (df[value_col] < lower_bound) | (df[value_col] > upper_bound)

    elif method == "isolation_forest":
        # Unsupervised ML anomaly detection
        try:
            from sklearn.ensemble import IsolationForest

            iso_forest = IsolationForest(contamination=0.05, random_state=42)
            df["is_anomaly"] = iso_forest.fit_predict(df[[value_col]]) == -1
        except ImportError:
            # Fallback to Z-score
            mean = df[value_col].mean()
            std = df[value_col].std() or 1
            df["z_score"] = (df[value_col] - mean) / std
            df["is_anomaly"] = df["z_score"].abs() > z_threshold

    elif method == "ewma":
        # Exponential weighted moving average (time-series aware)
        ewma = df[value_col].ewm(span=5).mean()
        ewma_std = df[value_col].rolling(window=5).std()
        df["is_anomaly"] = (df[value_col] - ewma).abs() > 2 * ewma_std

    else:
        # Default to Z-score
        mean = df[value_col].mean()
        std = df[value_col].std() or 1
        df["z_score"] = (df[value_col] - mean) / std
        df["is_anomaly"] = df["z_score"].abs() > z_threshold

    return df


# ── Risk score ────────────────────────────────────────────────────────────


def compute_risk_score(df: pd.DataFrame) -> Dict[str, float | int | str]:
    volatility = 0.0
    if not df.empty:
        series = df.groupby("period")["value"].sum().pct_change().dropna()
        volatility = float(series.std() * 100) if not series.empty else 0

    anomalies = detect_anomalies(df)
    anomaly_count = int(anomalies["is_anomaly"].sum()) if not anomalies.empty else 0

    concentration = 0.0
    if not df.empty:
        latest = df.sort_values("period").groupby("metric").tail(1)
        total = latest["value"].abs().sum()
        if total:
            share = latest["value"].abs() / total
            concentration = float(
                share.sort_values(ascending=False).head(3).sum() * 100
            )

    score = float(
        np.clip(
            100 - (volatility * 1.5 + anomaly_count * 5 + concentration * 0.4), 0, 100
        )
    )

    label_map = {
        "en": {70: "Low", 50: "Moderate", 0: "High"},
        "fr": {70: "Faible", 50: "Modéré", 0: "Élevé"},
    }
    lang_map = label_map.get(I18N.lang(), label_map["en"])
    label = next(v for k, v in sorted(lang_map.items(), reverse=True) if score >= k)

    return {
        "score": score,
        "label": label,
        "volatility": volatility,
        "anomaly_count": anomaly_count,
        "volatility_score": float(np.clip(volatility * 2, 0, 100)),
        "anomaly_score": float(np.clip(anomaly_count * 10, 0, 100)),
        "concentration_score": float(np.clip(concentration, 0, 100)),
        "liquidity_score": float(np.clip(100 - volatility * 1.2, 0, 100)),
        "execution_score": float(np.clip(100 - anomaly_count * 8, 0, 100)),
    }


# ── Metric changes (period-over-period) ──────────────────────────────────


def compute_metric_changes(df: pd.DataFrame) -> Dict[str, Dict[str, float | str]]:
    results: Dict[str, Dict[str, float | str]] = {}
    if df.empty:
        return results
    for metric, group in df.groupby("metric"):
        group = group.sort_values("period")
        latest = group.iloc[-1]["value"]
        previous = group.iloc[-2]["value"] if len(group) > 1 else np.nan
        delta = latest - previous if not np.isnan(previous) else np.nan
        delta_label = f"{delta:+.1f}" if not np.isnan(delta) else "—"
        results[metric] = {"latest": latest, "delta": delta, "delta_label": delta_label}
    return results


# ── Executive summary ─────────────────────────────────────────────────────


def build_executive_summary(
    df: pd.DataFrame,
    health: Dict[str, float | str],
    risk: Dict[str, float | str],
    key_metrics: Dict[str, float],
) -> List[str]:
    fr = I18N.lang() == "fr"
    bullets: List[str] = []
    if fr:
        bullets.append(
            f"Indice de santé à {health.get('score', 0):.0f} ({health.get('label')})."
        )
        risk_label = risk.get('label')
        volatility = risk.get('volatility', 0)
        bullets.append(
            f"Posture de risque : {risk_label} avec volatilité {volatility:.1f} %."
        )
        if not np.isnan(key_metrics.get("revenue", np.nan)):
            bullets.append(
                f"Revenu actuel à {format_number(key_metrics.get('revenue'))}."
            )
        if not np.isnan(key_metrics.get("gross_margin", np.nan)):
            bullets.append(
                f"Marge brute à {format_number(key_metrics.get('gross_margin'))}."
            )
        if not np.isnan(key_metrics.get("cash", np.nan)):
            bullets.append(f"Trésorerie à {format_number(key_metrics.get('cash'))}.")
    else:
        bullets.append(
            f"Health index at {health.get('score', 0):.0f} ({health.get('label')})."
        )
        bullets.append(
            f"Risk posture: {risk.get('label')} with volatility {risk.get('volatility', 0):.1f}%."
        )
        if not np.isnan(key_metrics.get("revenue", np.nan)):
            bullets.append(
                f"Revenue currently at {format_number(key_metrics.get('revenue'))}."
            )
        if not np.isnan(key_metrics.get("gross_margin", np.nan)):
            bullets.append(
                f"Gross margin pool at {format_number(key_metrics.get('gross_margin'))}."
            )
        if not np.isnan(key_metrics.get("cash", np.nan)):
            bullets.append(
                f"Cash visibility at {format_number(key_metrics.get('cash'))}."
            )
    return bullets


# ── Target attainment ─────────────────────────────────────────────────────


def compute_target_attainment(
    kpi_df: pd.DataFrame, targets_df: pd.DataFrame
) -> pd.DataFrame:
    if kpi_df.empty or targets_df.empty:
        return pd.DataFrame()

    latest = kpi_df.sort_values("period").groupby("metric").tail(1)
    merged = latest.merge(targets_df, on="metric", how="inner")

    def _status(row: pd.Series) -> str:
        actual, target = row["value"], row["target"]
        good = row.get("good_threshold")
        bad = row.get("bad_threshold")
        direction = row.get("direction", "higher_is_better")

        if direction == "lower_is_better":
            actual, target = -actual, -target if pd.notna(target) else target
            good = -good if pd.notna(good) else good
            bad = -bad if pd.notna(bad) else bad

        if pd.notna(good) and actual >= good:
            return t("COMMON", "on_track") if I18N.lang() == "fr" else "On Track"
        if pd.notna(bad) and actual < bad:
            return t("COMMON", "at_risk") if I18N.lang() == "fr" else "At Risk"
        if pd.notna(target) and actual >= target:
            return t("COMMON", "on_track") if I18N.lang() == "fr" else "On Track"
        return "Needs Attention" if I18N.lang() != "fr" else "Attention requise"

    merged["status"] = merged.apply(_status, axis=1)
    merged["delta_vs_target"] = merged["value"] - merged["target"]
    return merged[["metric", "value", "target", "delta_vs_target", "status"]]
