"""
Admin API endpoints for AgentKit - scenario switching, database info, user management
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
from datetime import datetime

# Try to import database services
try:
    from agentkit_mcp.services.pg_store import get_kpi_metrics
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

router = APIRouter()

# Scenario definitions matching frontend
SCENARIOS = [
    "healthy",
    "declining_revenue",
    "high_churn",
    "forecast_uncertainty",
    "anomaly_spike",
    "seasonal_variance",
    "recovery_mode"
]

# In-memory storage for demo (in production, use database)
current_scenario = "healthy"
users_db = []
audit_log = []


@router.get("/scenario")
async def get_current_scenario() -> Dict:
    """Get currently active data scenario"""
    return {"current_scenario": current_scenario}


@router.post("/scenario")
async def switch_scenario(scenario_data: Dict) -> Dict:
    """Switch to a different data scenario"""
    global current_scenario

    scenario_id = scenario_data.get("scenario")
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {scenario_id}")

    current_scenario = scenario_id

    # Log the scenario switch
    audit_log.append({
        "timestamp": datetime.now().isoformat(),
        "action": "scenario_switch",
        "details": f"Switched to scenario: {scenario_id}",
        "username": "admin"
    })

    return {"status": "success", "current_scenario": current_scenario}


@router.get("/database/info")
async def get_database_info() -> Dict:
    """Get database connection and statistics information"""
    if not DB_AVAILABLE:
        return {
            "connected": False,
            "total_records": 0,
            "categories": 0,
            "metric_types": 0,
            "date_range": "N/A",
            "finance_available": False,
            "people_available": False,
            "forecast_available": False,
            "anomaly_available": False
        }

    try:
        # Get database statistics
        metrics = get_kpi_metrics()

        # Calculate statistics
        total_records = len(metrics)
        categories = len(set(m.get("category", "") for m in metrics))
        metric_types = len(set(m.get("metric", "") for m in metrics))

        dates = [m.get("date") for m in metrics if m.get("date")]
        date_range = f"{min(dates)} to {max(dates)}" if dates else "N/A"

        # Check data availability
        finance_available = any(m.get("category") == "Finance" for m in metrics)
        people_available = any(m.get("category") == "People" for m in metrics)
        forecast_available = any(m.get("category") == "Forecasting" for m in metrics)
        anomaly_available = any(m.get("category") == "Anomalies" for m in metrics)

        return {
            "connected": True,
            "total_records": total_records,
            "categories": categories,
            "metric_types": metric_types,
            "date_range": date_range,
            "finance_available": finance_available,
            "people_available": people_available,
            "forecast_available": forecast_available,
            "anomaly_available": anomaly_available
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "total_records": 0,
            "categories": 0,
            "metric_types": 0,
            "date_range": "N/A",
            "finance_available": False,
            "people_available": False,
            "forecast_available": False,
            "anomaly_available": False
        }


@router.get("/users")
async def list_users() -> Dict:
    """List all users (passwords never leave the server, even for this in-memory demo store)"""
    return {"users": [{k: v for k, v in u.items() if k != "password"} for u in users_db]}


@router.post("/register")
async def register_user(user_data: Dict) -> Dict:
    """Register a new user"""
    username = user_data.get("username")
    password = user_data.get("password")
    role = user_data.get("role", "viewer")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    # Check if user already exists
    if any(u.get("username") == username for u in users_db):
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create new user
    new_user = {
        "id": len(users_db) + 1,
        "username": username,
        "password": password,  # In production, hash this!
        "full_name": user_data.get("full_name", ""),
        "role": role,
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }

    users_db.append(new_user)

    # Log user creation
    audit_log.append({
        "timestamp": datetime.now().isoformat(),
        "action": "user_created",
        "details": f"Created user: {username} with role: {role}",
        "username": "admin"
    })

    return {"status": "success", "user": {"id": new_user["id"], "username": username, "role": role}}


@router.patch("/users/{user_id}")
async def update_user(user_id: int, updates: Dict) -> Dict:
    """Update user information"""
    user = next((u for u in users_db if u.get("id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user fields
    for key, value in updates.items():
        if key in user:
            user[key] = value

    # Log user update
    audit_log.append({
        "timestamp": datetime.now().isoformat(),
        "action": "user_updated",
        "details": f"Updated user {user_id}: {updates}",
        "username": "admin"
    })

    return {"status": "success", "user": user}


@router.get("/audit-log")
async def get_audit_log(limit: int = 150) -> Dict:
    """Get audit log entries"""
    return {"logs": audit_log[-limit:]}


@router.get("/roles")
async def list_roles() -> Dict:
    """List available roles and their permissions"""
    roles = {
        "admin": {
            "description": "Full system access including user management",
            "permissions": ["read", "write", "delete", "admin"]
        },
        "executive": {
            "description": "High-level business intelligence access",
            "permissions": ["read", "write"]
        },
        "manager": {
            "description": "Team-level analytics and reporting",
            "permissions": ["read", "write"]
        },
        "analyst": {
            "description": "Data analysis and reporting tools",
            "permissions": ["read", "write"]
        },
        "viewer": {
            "description": "Read-only access to dashboards",
            "permissions": ["read"]
        }
    }
    return {"roles": roles}
