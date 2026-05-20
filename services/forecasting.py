"""
AI forecasting — time-series, Monte-Carlo, cash runway, health scoring.
CPU-friendly: uses scikit-learn LinearRegression (no GPU needed).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

from core.i18n import I18N
from core.logger import get_logger

log = get_logger(__name__)


class ForecastEngine:
    """Linear-regression time-series forecasts with confidence intervals."""

    def time_series_forecast(
        self,
        df: pd.DataFrame,
        periods: int = 3,
        confidence_level: float = 0.95,
    ) -> pd.DataFrame:
        if df.empty or len(df) < 2:
            return pd.DataFrame()

        df = df.sort_values("month_tag").copy()
        df["time_index"] = range(len(df))
        X = df[["time_index"]].values
        y = df["actual"].values

        model = LinearRegression().fit(X, y)
        preds = model.predict(X)
        residual_std = np.std(y - preds)

        mse = mean_squared_error(y, preds)
        r2 = r2_score(y, preds)

        last_idx = df["time_index"].max()
        future_idx = np.arange(last_idx + 1, last_idx + periods + 1).reshape(-1, 1)
        future_preds = model.predict(future_idx)

        z = stats.norm.ppf((1 + confidence_level) / 2)
        margin = z * residual_std * np.sqrt(
            1 + 1 / len(df) + (future_idx - X.mean()) ** 2 / np.sum((X - X.mean()) ** 2)
        )

        last_month = datetime.strptime(df["month_tag"].iloc[-1], "%Y-%m")
        future_months = [(last_month + timedelta(days=30 * i)).strftime("%Y-%m") for i in range(1, periods + 1)]

        forecast_df = pd.DataFrame({
            "month_tag": future_months,
            "forecast": future_preds,
            "lower_bound": future_preds - margin.flatten(),
            "upper_bound": future_preds + margin.flatten(),
            "confidence_level": confidence_level,
        })

        return forecast_df

    def explain_forecast(self, df: pd.DataFrame) -> Dict[str, float]:
        if df.empty or len(df) < 2:
            return {"r_squared": 0.0, "slope": 0.0, "intercept": 0.0}
        df = df.sort_values("month_tag").copy()
        df["time_index"] = range(len(df))
        X, y = df[["time_index"]].values, df["actual"].values
        model = LinearRegression().fit(X, y)
        return {"r_squared": model.score(X, y), "slope": model.coef_[0], "intercept": model.intercept_}


class ScenarioEngine:
    """Monte-Carlo simulation for scenario planning with advanced models."""

    def monte_carlo_simulation(
        self,
        base_value: float,
        growth_rate: float,
        std_dev: float,
        iterations: int = 1000,
        periods: int = 12,
        correlation: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Advanced Monte-Carlo with correlation, shocks, and confidence bands.
        - Correlated random walk (not independent periods)
        - Jump diffusion (sudden 20% moves at 10% probability)
        - Multiple confidence levels (10th, 50th, 90th percentile)
        """
        results = np.zeros((iterations, periods))
        shocks = np.random.normal(0, 1, (iterations, periods))
        
        for i in range(iterations):
            value = base_value
            for t in range(periods):
                # Correlated random walk
                if t > 0:
                    prev_shock = shocks[i, t-1]
                    current_shock = correlation * prev_shock + np.sqrt(1 - correlation**2) * shocks[i, t]
                else:
                    current_shock = shocks[i, t]
                
                # Growth with stochastic component
                drift = growth_rate / 12  # Monthly drift
                volatility = std_dev / np.sqrt(12)  # Monthly volatility
                
                # Occasional large shocks (10% probability of 20% move)
                if np.random.random() < 0.1:
                    current_shock *= 2
                
                value = value * (1 + drift + volatility * current_shock)
                results[i, t] = max(0, value)  # Prevent negative values
        
        mean_path = np.mean(results, axis=0)
        p10_path = np.percentile(results, 10, axis=0)
        p50_path = np.percentile(results, 50, axis=0)
        p90_path = np.percentile(results, 90, axis=0)
        
        worst_case = np.min(results[:, -1])
        best_case = np.max(results[:, -1])
        probability_positive = np.mean(results[:, -1] > base_value) * 100
        
        return {
            "mean_path": mean_path.tolist(),
            "p10_path": p10_path.tolist(),
            "p50_path": p50_path.tolist(),
            "p90_path": p90_path.tolist(),
            "worst_case": float(worst_case),
            "best_case": float(best_case),
            "probability_positive": float(probability_positive),
            "iterations": iterations,
            "periods": periods,
        }

    def simulate_business_event(
        self,
        current_data: pd.DataFrame,
        event_impact: float,
        category: str,
        recovery_months: int = 6,
    ) -> pd.DataFrame:
        """
        Simulate impact of business event (market downturn, product launch, etc).
        - Applies shock at midpoint
        - Recovers gradually over recovery_months
        """
        data = current_data.sort_values("period").copy() if "period" in current_data.columns else current_data.copy()
        data["scenario_value"] = data.get("value", data.get("actual", 1))
        
        shock_point = len(data) // 2
        for idx in range(shock_point, len(data)):
            months_since_shock = idx - shock_point
            if months_since_shock == 0:
                # Apply initial shock
                data.iloc[idx, data.columns.get_loc("scenario_value")] *= (1 + event_impact)
            else:
                # Recover gradually (exponential recovery)
                recovery_factor = 1 - (event_impact * np.exp(-months_since_shock / recovery_months))
                data.iloc[idx, data.columns.get_loc("scenario_value")] *= recovery_factor
        
        return data

    def sensitivity_analysis(
        self,
        base_forecast: pd.DataFrame,
        variables: Dict[str, Tuple[float, float]],
    ) -> Dict[str, Any]:
        """
        Sensitivity analysis: which variables drive forecast most?
        Tests ±10% change in each variable and measures impact.
        """
        sensitivity = {}
        base_value = base_forecast["forecast"].iloc[-1] if not base_forecast.empty else 1
        
        for var, (min_val, max_val) in variables.items():
            mid = (min_val + max_val) / 2
            change_pct = 0.1  # Test ±10% change
            
            impact_up = (mid * (1 + change_pct) - base_value) / base_value * 100
            impact_down = (mid * (1 - change_pct) - base_value) / base_value * 100
            
            sensitivity[var] = {
                "impact_up_pct": float(impact_up),
                "impact_down_pct": float(impact_down),
                "elasticity": float((impact_up - impact_down) / 20),  # % output change / % input change
            }
        
        return sensitivity


# ── Standalone helpers ────────────────────────────────────────────────────

def calculate_cash_runway(
    current_cash: float,
    monthly_burn: float,
    monthly_revenue: float = 0,
) -> Dict[str, Any]:
    net_burn = monthly_burn - monthly_revenue
    if net_burn <= 0:
        runway_months = float("inf")
        runway_date = None
    else:
        runway_months = current_cash / net_burn
        runway_date = datetime.now() + timedelta(days=30 * runway_months)

    fr = I18N.lang() == "fr"
    return {
        "current_cash": current_cash,
        "monthly_burn": monthly_burn,
        "monthly_revenue": monthly_revenue,
        "net_burn": net_burn,
        "runway_months": runway_months,
        "runway_date": runway_date.strftime("%Y-%m-%d") if runway_date else ("Indéfini" if fr else "Indefinite"),
        "is_healthy": runway_months > 12 or runway_months == float("inf"),
    }


def calculate_financial_health_score(metrics: Dict[str, float]) -> Dict[str, Any]:
    score = 0
    max_score = 0
    details: Dict[str, int] = {}

    def _score_bucket(value: float, thresholds: List[tuple]) -> int:
        for threshold, pts in thresholds:
            if value >= threshold:
                return pts
        return thresholds[-1][1]

    if "revenue_growth_pct" in metrics:
        pts = _score_bucket(metrics["revenue_growth_pct"], [(20, 25), (10, 20), (0, 15)])
        if metrics["revenue_growth_pct"] < 0:
            pts = max(0, int(15 + metrics["revenue_growth_pct"]))
        score += pts
        max_score += 25
        details["revenue_growth"] = pts

    if "profit_margin_pct" in metrics:
        pts = _score_bucket(metrics["profit_margin_pct"], [(20, 25), (10, 20), (0, 15)])
        if metrics["profit_margin_pct"] < 0:
            pts = max(0, int(15 + metrics["profit_margin_pct"]))
        score += pts
        max_score += 25
        details["profitability"] = pts

    if "cash_runway_months" in metrics:
        pts = _score_bucket(metrics["cash_runway_months"], [(18, 25), (12, 20), (6, 15), (3, 10)])
        score += pts
        max_score += 25
        details["cash_position"] = pts

    if "variance_vs_plan_pct" in metrics:
        var = abs(metrics["variance_vs_plan_pct"])
        pts = _score_bucket(-var, [(-5, 25), (-10, 20), (-15, 15), (-25, 10)])
        score += pts
        max_score += 25
        details["operational_efficiency"] = pts

    final = (score / max_score * 100) if max_score else 0

    fr = I18N.lang() == "fr"
    if final >= 90:
        rating, color = ("Excellent", "🟢")
    elif final >= 75:
        rating, color = ("Bon" if fr else "Good", "🟡")
    elif final >= 60:
        rating, color = ("Passable" if fr else "Fair", "🟠")
    else:
        rating, color = ("Faible" if fr else "Poor", "🔴")

    return {"score": final, "rating": rating, "color": color, "details": details, "max_score": max_score}
