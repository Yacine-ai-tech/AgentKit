"""AgentKit KPI data seed for OmniSmart Corp — multi-domain metrics for MCP tools.

Generates realistic KPI data for OmniSmart Corp across 10 domains:
- Finance KPIs (revenue, profit, margins, forecasting)
- People KPIs (headcount, turnover, hiring, retention)
- Operations KPIs (supply chain, warehouse, defects)
- Customer KPIs (NPS, churn, LTV, support)
- Engineering KPIs (deploy frequency, MTTR, sprint velocity)
- Growth KPIs (MRR/ARR, expansion, net revenue retention)
- Logistics KPIs (freight, shipment timing, inventory turnover)
- ESG KPIs (emissions, renewable energy, board diversity, ethics audits)
- IT KPIs (uptime, SLA compliance, infrastructure cost, patch compliance)
- Security KPIs (vulnerabilities, incident response, phishing resilience)
- Anomaly detection data (outliers, unusual patterns)
- Forecasting data (projections, predictions)

The first 5 domains were the original set; Growth/Logistics/ESG/IT mirror IntelAI's
own 7-domain taxonomy for cross-portfolio consistency, and Security is a domain neither
project covered before — chosen deliberately so AgentKit's own KPI surface goes beyond
IntelAI's rather than just duplicating it.

Run standalone: python -m agentkit_mcp.data.seed
Or from code: from agentkit_mcp.data.seed import seed_agentkit_database; seed_agentkit_database()
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from src.agentkit_mcp.services.pg_store import insert_kpi_metric

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print(
        "Warning: Database modules not available. This script can still generate data."
    )

SEED = 42
MONTHS = 24  # 2 years of historical data
SCENARIOS = [
    "healthy",
    "declining_revenue",
    "high_churn",
    "forecast_uncertainty",
    "anomaly_spike",
    "seasonal_variance",
    "recovery_mode",
]

# Business KPI definitions for OmniSmart Corp
BUSINESS_KPIS = {
    "Finance": [
        ("Monthly_Revenue", "USD", 500_000, 0.02, "up"),
        ("Profit_Margin", "%", 25, 0.01, "up"),
        ("Operating_Expenses", "USD", 375_000, 0.015, "down"),
        ("Cash_Burn_Rate", "USD", 150_000, -0.02, "down"),
        ("Customer_Acquisition_Cost", "USD", 500, 0.05, "down"),
    ],
    "People": [
        ("Headcount", "count", 120, 0.01, "up"),
        ("Employee_Turnover_Rate", "%", 12, -0.01, "down"),
        ("Hiring_Rate", "%", 8, 0.02, "up"),
        ("Remote_Work_Percentage", "%", 65, 0.005, "up"),
        ("Employee_Satisfaction_Score", "score", 7.5, 0.01, "up"),
    ],
    "Operations": [
        ("Supply_Chain_Fulfillment_Rate", "%", 94, 0.005, "up"),
        ("Average_Order_Processing_Time", "hours", 2.3, -0.02, "down"),
        ("Warehouse_Utilization", "%", 78, 0.01, "up"),
        ("Supplier_On_Time_Delivery", "%", 88, 0.01, "up"),
        ("Production_Defect_Rate", "%", 1.2, -0.05, "down"),
    ],
    "Customer": [
        ("NPS_Score", "score", 42, 0.02, "up"),
        ("Customer_Churn_Rate", "%", 5.2, -0.02, "down"),
        ("Support_Ticket_Resolution_Time", "hours", 4.1, -0.02, "down"),
        ("Customer_Lifetime_Value", "USD", 2400, 0.03, "up"),
        ("Product_Adoption_Rate", "%", 67, 0.01, "up"),
    ],
    "Engineering": [
        ("Deployment_Frequency", "per_week", 3.2, 0.05, "up"),
        ("MTTR", "hours", 1.8, -0.03, "down"),
        ("Change_Failure_Rate", "%", 4.1, -0.02, "down"),
        ("Sprint_Velocity", "points", 47, 0.02, "up"),
        ("Code_Review_Turnaround", "hours", 6.2, -0.02, "down"),
    ],
    "Growth": [
        ("Monthly_Recurring_Revenue", "USD", 180_000, 0.03, "up"),
        ("Annual_Recurring_Revenue", "USD", 2_200_000, 0.03, "up"),
        ("New_Customer_Growth_Rate", "%", 8, 0.01, "up"),
        ("Expansion_Revenue", "USD", 45_000, 0.02, "up"),
        ("Net_Revenue_Retention", "%", 108, 0.005, "up"),
    ],
    "Logistics": [
        ("Freight_Cost_Per_Unit", "USD", 4.2, -0.01, "down"),
        ("On_Time_Shipment_Rate", "%", 91, 0.005, "up"),
        ("Inventory_Turnover_Ratio", "ratio", 6.5, 0.01, "up"),
        ("Last_Mile_Delivery_Time", "hours", 18, -0.02, "down"),
        ("Carrier_Damage_Rate", "%", 0.8, -0.03, "down"),
    ],
    "ESG": [
        ("Carbon_Emissions_Per_Unit", "kg_co2", 2.1, -0.02, "down"),
        ("Renewable_Energy_Percentage", "%", 42, 0.02, "up"),
        ("Board_Diversity_Ratio", "%", 38, 0.01, "up"),
        ("Waste_Recycling_Rate", "%", 55, 0.015, "up"),
        ("Supplier_Ethics_Audit_Score", "score", 8.1, 0.005, "up"),
    ],
    "IT": [
        ("System_Uptime", "%", 99.7, 0.001, "up"),
        ("Ticket_Resolution_SLA_Compliance", "%", 92, 0.01, "up"),
        ("Infrastructure_Cost_Per_User", "USD", 18, -0.01, "down"),
        ("Patch_Compliance_Rate", "%", 87, 0.01, "up"),
        ("Network_Latency_P95", "ms", 45, -0.02, "down"),
    ],
    "Security": [
        ("Critical_Vulnerabilities_Open", "count", 12, -0.05, "down"),
        ("Mean_Time_To_Remediate", "hours", 36, -0.03, "down"),
        ("Phishing_Test_Failure_Rate", "%", 9, -0.02, "down"),
        ("Security_Incident_Count", "count", 3, -0.04, "down"),
        ("Access_Review_Completion_Rate", "%", 84, 0.015, "up"),
    ],
    "Forecasting": [
        ("Revenue_Forecast_3mo", "USD", 550_000, 0.01, "up"),
        ("Headcount_Forecast_3mo", "count", 125, 0.01, "up"),
        ("Profit_Forecast_3mo", "USD", 580_000, 0.015, "up"),
        ("Customer_Forecast_3mo", "count", 520, 0.02, "up"),
    ],
    "Anomalies": [
        ("Unusual_Expense_Spike", "USD", 0, 0, "down"),
        ("Anomaly_Score", "score", 0, 0, "down"),
        ("Outlier_Detection_Flag", "boolean", 0, 0, "down"),
    ],
}


def generate_scenario_data(
    scenario: str, base_value: float, drift: float, direction: str, month: int
) -> float:
    """Generate scenario-specific data patterns"""
    random.seed(SEED + month + hash(scenario) % 1000)

    if scenario == "healthy":
        # Normal growth/decline according to drift
        month_factor = 1 + (drift * month * (1 if direction == "up" else -1))
        noise = random.uniform(-0.05, 0.05)  # 5% noise
        return base_value * month_factor * (1 + noise)

    elif scenario == "declining_revenue":
        # Revenue declining faster than normal
        if month < 6:
            return base_value * (1 - 0.1 * month)  # Sharp decline
        else:
            return base_value * 0.4  # Stabilized at 40% of baseline

    elif scenario == "high_churn":
        # High employee turnover/churn
        if "Turnover" in scenario or "Retention" in scenario or "Churn" in scenario:
            return base_value * (1 + 0.2 * month)  # Increasing turnover/churn
        return base_value  # Other metrics normal

    elif scenario == "forecast_uncertainty":
        # Forecasts become less accurate over time
        uncertainty = 0.1 * month
        noise = random.uniform(-uncertainty, uncertainty)
        return base_value * (1 + noise)

    elif scenario == "anomaly_spike":
        # Occasional spikes in expenses
        if month == 12:  # Mid-year spike
            return base_value * 3.0
        elif month == 18:  # Another spike
            return base_value * 2.5
        return base_value

    elif scenario == "seasonal_variance":
        # Seasonal patterns (Q4 bump, Q1 dip)
        quarter = (month % 12) // 3
        seasonal_factor = 1.0
        if quarter == 3:  # Q4
            seasonal_factor = 1.15
        elif quarter == 0:  # Q1
            seasonal_factor = 0.85
        return base_value * seasonal_factor

    elif scenario == "recovery_mode":
        # Recovery from previous decline
        if month < 3:
            return base_value * 0.7  # Starting low
        else:
            recovery = min(1.0, 0.7 + (0.1 * (month - 2)))
            return base_value * recovery

    return base_value  # Default to healthy


def generate_time_series_data(scenario: str = "healthy") -> List[Dict]:
    """Generate time series data for all KPIs based on scenario"""
    data = []
    base_date = datetime.now() - timedelta(days=MONTHS * 30)

    for month in range(MONTHS):
        current_date = base_date + timedelta(days=month * 30)

        for category, kpis in BUSINESS_KPIS.items():
            for metric, unit, base_value, drift, direction in kpis:
                value = generate_scenario_data(
                    scenario, base_value, drift, direction, month
                )

                # Add some randomness for anomaly detection
                if category == "Anomalies" and scenario == "healthy":
                    # Small chance of random anomalies
                    if random.random() < 0.05:  # 5% chance
                        value = base_value * random.uniform(0.5, 3.0)

                data.append(
                    {
                        "category": category,
                        "metric": metric,
                        "unit": unit,
                        "value": value,
                        "date": current_date.strftime("%Y-%m-%d"),
                        "scenario": scenario,
                    }
                )

    return data


def seed_database(data: List[Dict]) -> bool:
    """Seed database with generated KPI data"""
    if not DB_AVAILABLE:
        print("Database not available - data generation only")
        return False

    try:
        # Clear existing data
        print("Clearing existing KPI data...")
        # This would require a delete function in pg_store

        # Insert new data
        print(f"Seeding {len(data)} KPI records...")
        success_count = 0

        for record in data:
            try:
                insert_kpi_metric(
                    category=record["category"],
                    metric=record["metric"],
                    value=record["value"],
                    unit=record["unit"],
                    date_str=record["date"],
                )
                success_count += 1
            except Exception as e:
                print(f"Failed to insert {record['metric']}: {e}")

        print(f"Successfully seeded {success_count}/{len(data)} records")
        return success_count > 0

    except Exception as e:
        print(f"Database seeding failed: {e}")
        return False


def generate_scenario_summary() -> Dict:
    """Generate summary of each scenario for documentation"""
    summaries = {}

    for scenario in SCENARIOS:
        data = generate_time_series_data(scenario)

        # Calculate summary statistics
        finance_revenue = [d["value"] for d in data if d["metric"] == "Monthly_Revenue"]
        people_headcount = [d["value"] for d in data if d["metric"] == "Headcount"]

        summaries[scenario] = {
            "total_records": len(data),
            "avg_revenue": (
                sum(finance_revenue) / len(finance_revenue) if finance_revenue else 0
            ),
            "final_revenue": finance_revenue[-1] if finance_revenue else 0,
            "avg_headcount": (
                sum(people_headcount) / len(people_headcount) if people_headcount else 0
            ),
            "final_headcount": people_headcount[-1] if people_headcount else 0,
            "trend": "growing" if scenario == "healthy" else "varying",
        }

    return summaries


def main():
    print("=== AgentKit KPI Data Seeder ===")
    print("Generating OmniSmart Corp data for MCP tools\n")

    # Generate data for each scenario
    all_data = {}
    scenario_summaries = {}

    for scenario in SCENARIOS:
        print(f"Generating data for scenario: {scenario}")
        data = generate_time_series_data(scenario)
        all_data[scenario] = data
        scenario_summaries[scenario] = generate_scenario_summary()

    # Print scenario summaries
    print("\n=== Scenario Summaries ===")
    for scenario, summary in scenario_summaries.items():
        print(f"\n{scenario.upper()}:")
        print(f"  Records: {summary['total_records']}")
        print(f"  Avg Revenue: ${summary['avg_revenue']:,.0f}")
        print(f"  Final Revenue: ${summary['final_revenue']:,.0f}")
        print(f"  Avg Headcount: {summary['avg_headcount']:.1f}")
        print(f"  Final Headcount: {summary['final_headcount']:.1f}")
        print(f"  Trend: {summary['trend']}")

    # Seed with healthy scenario by default
    print("\n=== Seeding Database with 'healthy' scenario ===")
    healthy_data = all_data["healthy"]
    success = seed_database(healthy_data)

    if success:
        print("✅ Database seeded successfully")
        print(f"Generated {len(healthy_data)} KPI records over {MONTHS} months")
        print("Other scenarios available for testing: " + ", ".join(SCENARIOS[1:]))
    else:
        print("⚠️  Database seeding failed (DB may not be available)")
        print("Data generation complete - can be used for mock responses")

    return all_data

def seed_agentkit_database():
    """Alias for backwards compatibility."""
    return main()

if __name__ == "__main__":
    main()
