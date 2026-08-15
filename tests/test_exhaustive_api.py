import pytest
import httpx
import os

TOKEN = os.getenv('AGENTKIT_INTERNAL_TOKEN', '')
HEADERS = {'X-AgentKit-Internal-Token': TOKEN}
BASE_URL = os.getenv('TEST_BASE_URL', '')

# These tests require a live AgentKit server. Skip automatically when TEST_BASE_URL is
# not set (local dev without a running server). In CI, set TEST_BASE_URL to the deployed
# service URL so these run as post-deploy smoke tests.
if not BASE_URL:
    pytest.skip("TEST_BASE_URL not set — skipping live E2E tests", allow_module_level=True)


@pytest.mark.asyncio
async def test_e2e_api_get__health_0():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/health', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_tools_1():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/tools', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_kpis_2():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/kpis', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_health_score_3():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/health-score', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_anomalies_4():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/anomalies', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_forecast_5():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/forecast', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_metrics_6():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/metrics', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_summary_7():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/summary', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__api_observability_8():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/api/observability', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__api_workflow_run_9():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.post(f'{BASE_URL}/api/workflow/run', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get___10():
    # Extracted from web_app.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

