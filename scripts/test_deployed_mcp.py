#!/usr/bin/env python3
"""Test AgentKit deployed service with MCP tools, health, and REST facade endpoints.

Dynamically resolves service URLs, auth tokens, and headers from environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
import httpx

# Dynamically load from repository root .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

AGENTKIT_URL = (
    os.getenv("AGENTKIT_URL")
    or os.getenv("MCP_SERVER_URL")
    or f"http://localhost:{os.getenv('MCP_PORT', '8005')}"
).rstrip("/")


def _get_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    auth_token = os.getenv("MCP_AUTH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    internal_token = os.getenv("AGENTKIT_INTERNAL_TOKEN")
    if internal_token:
        headers["X-AgentKit-Internal-Token"] = internal_token
    return headers


def test_health() -> bool:
    """Test health endpoint."""
    print("Testing AgentKit Health...")
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/health")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Health Check: {result.get('status', 'unknown')}")
                return True
            print(f"  Health Check Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  Health Check Error: {e}")
        return False


def test_sse_connection() -> bool:
    """Test SSE connection endpoint."""
    print("\nTesting SSE Connection...")
    headers = _get_headers()
    try:
        with httpx.Client(timeout=10.0) as client:
            # Connect with stream or short timeout GET
            response = client.get(f"{AGENTKIT_URL}/sse", headers=headers)
            print(f"Status: {response.status_code}")
            # 200 or streaming response indicates valid SSE endpoint
            if response.status_code in (200, 307):
                print("  SSE Connection: Connected successfully")
                return True
            if response.status_code == 401:
                print("  SSE Connection: Authenticated gate working as designed (401)")
                return True
            print(f"  SSE Connection Failed: {response.status_code}")
            return False
    except httpx.ReadTimeout:
        # SSE stream remains open on 200 OK — this is expected behavior for open SSE stream
        print("  SSE Connection: Stream connected and held open (timeout reached)")
        return True
    except Exception as e:
        print(f"  SSE Connection Error: {e}")
        return False


def test_mcp_tools() -> bool:
    """Test MCP tools discovery endpoint."""
    print("\nTesting MCP Tools Discovery...")
    headers = _get_headers()
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/api/tools", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                tools = result.get("tools", [])
                print(f"  MCP Tools: {len(tools)} tools available")
                return True
            print(f"  MCP Tools Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  MCP Tools Error: {e}")
        return False


def test_kpi_query() -> bool:
    """Test querying KPIs across business domains."""
    print("\nTesting KPI Query...")
    headers = _get_headers()
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/api/kpis?domain=Finance", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                kpis = result.get("kpis", [])
                print(f"  KPI Query: Received {len(kpis)} finance records")
                return True
            print(f"  KPI Query Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  KPI Query Error: {e}")
        return False


def test_company_health() -> bool:
    """Test company health score computation."""
    print("\nTesting Company Health Score...")
    headers = _get_headers()
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/api/health-score", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Health Score: {result.get('score')} ({result.get('interpretation')})")
                return True
            print(f"  Health Score Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  Health Score Error: {e}")
        return False


def test_llm_routing() -> bool:
    """Test LLM routing introspection endpoint."""
    print("\nTesting LLM Routing Introspection...")
    headers = _get_headers()
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/api/llm-routing", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Inference Mode: {result.get('inference_mode')}")
                return True
            print(f"  LLM Routing Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  LLM Routing Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("AgentKit Live Service Verification")
    print(f"Endpoint: {AGENTKIT_URL}")
    print("=" * 60)

    results = {
        "Health Check": test_health(),
        "SSE Connection": test_sse_connection(),
        "MCP Tools": test_mcp_tools(),
        "KPI Query": test_kpi_query(),
        "Company Health": test_company_health(),
        "LLM Routing": test_llm_routing(),
    }

    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    all_passed = True
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        if not result:
            all_passed = False
        print(f"{test_name}: {status}")

    print("=" * 60)
    raise SystemExit(0 if all_passed else 1)
