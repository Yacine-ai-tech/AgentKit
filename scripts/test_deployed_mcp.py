#!/usr/bin/env python3
"""
Test AgentKit deployed service with MCP tools and SSE connection
Tests the health, SSE, and MCP endpoints
"""
import httpx
import json
import asyncio

# Deployed service URL
AGENTKIT_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing AgentKit Health...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Health Check: {result.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Health Check Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        return False

def test_sse_connection():
    """Test SSE connection endpoint"""
    print("\nTesting SSE Connection...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/sse")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print(f"✅ SSE Connection: Connected successfully")
                return True
            else:
                print(f"❌ SSE Connection Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ SSE Connection Error: {e}")
        return False

def test_mcp_tools():
    """Test MCP tools endpoint"""
    print("\nTesting MCP Tools...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/api/tools")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ MCP Tools: {len(result.get('tools', []))} tools available")
                return True
            else:
                print(f"❌ MCP Tools Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ MCP Tools Error: {e}")
        return False

def test_mcp_tool_call():
    """Test calling an MCP tool"""
    print("\nTesting MCP Tool Call...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # Try to call a simple tool
            tool_call = {
                "tool": "get_kpi_data",
                "parameters": {
                    "domain": "hr",
                    "metric": "workforce_summary"
                }
            }
            
            response = client.post(f"{AGENTKIT_URL}/api/tools/call", json=tool_call)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ MCP Tool Call: {result}")
                return True
            else:
                print(f"❌ MCP Tool Call Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ MCP Tool Call Error: {e}")
        return False

def test_admin_kpi():
    """Test admin KPI endpoint"""
    print("\nTesting Admin KPI...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AGENTKIT_URL}/api/admin/kpi")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Admin KPI: {result}")
                return True
            else:
                print(f"❌ Admin KPI Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Admin KPI Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AgentKit Testing Against Deployed Service")
    print("=" * 60)
    
    results = {
        "Health Check": test_health(),
        "SSE Connection": test_sse_connection(),
        "MCP Tools": test_mcp_tools(),
        "MCP Tool Call": test_mcp_tool_call(),
        "Admin KPI": test_admin_kpi()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print("=" * 60)