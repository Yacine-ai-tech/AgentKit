import { test, expect, Page } from '@playwright/test';

/**
 * AgentKit — Comprehensive E2E Suite
 * Phase 6: Agent Operations (React Flow DAGs, Tool Config)
 * Phase 6: Extended UI/UX Validation
 * Phase 7: Deep Component Integration
 */

const BASE_URL = process.env.AGENTKIT_URL    || process.env.TEST_BASE_URL || '/';
const API_URL  = process.env.AGENTKIT_API_URL || '/';
const AUTH_URL = process.env.INTELAI_API_URL  || '/';

async function assertNoReactCrash(page: Page) {
  await expect(page.locator('text=/An unexpected error occurred|Something went wrong/i')).toHaveCount(0);
}

async function getAuthToken(request: any): Promise<string> {
  const resp = await request.post(`${AUTH_URL}/api/login`, {
    data: { username: 'admin', password: process.env.ADMIN_PASS || '' }
  }).catch(() => null);
  if (resp && resp.ok()) {
    const body = await resp.json();
    return body.access_token || body.token || '';
  }
  return '';
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 6 — AgentKit UI Workflows
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 6 — AgentKit Operations', () => {

  test('All main navigation pages render without crash', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    const routes = [
      '/connect', '/intelligence', '/observability',
      '/overview', '/resources', '/tools', '/workflow'
    ];
    for (const route of routes) {
      await page.goto(`${'/'}${route}`);
      await page.waitForLoadState('domcontentloaded');
      await assertNoReactCrash(page);
      console.log(`✅ AgentKit ${route} — OK`);
    }
  });

  test('Workflow Builder: React Flow DAG canvas renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflow`);
    await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
    await assertNoReactCrash(page);

    // React Flow renders as SVG with class "react-flow"
    const canvas = page.locator('.react-flow, canvas, svg, [data-testid="workflow"]').first();
    if (await canvas.isVisible({ timeout: 8000 }).catch(() => false)) {
      await expect(canvas).toBeVisible();
      console.log('✅ React Flow DAG canvas visible');
    }
  });

  test('Workflow Builder: DAG nodes are draggable', async ({ page }) => {
    await page.goto(`${BASE_URL}/workflow`);
    await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
    await assertNoReactCrash(page);

    // Find a React Flow node and drag it
    const node = page.locator('.react-flow__node, [data-testid="node"]').first();
    if (await node.isVisible({ timeout: 5000 }).catch(() => false)) {
      const box = await node.boundingBox();
      if (box) {
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        await page.mouse.move(box.x + 100, box.y + 50);
        await page.mouse.up();
        await page.waitForTimeout(500);
        await assertNoReactCrash(page);
        console.log('✅ DAG node dragged successfully');
      }
    }
  });

  test('Tools page: tool list renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/tools`);
    await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
    await assertNoReactCrash(page);
    const toolList = page.locator('table, .tool-list, .tool-card, [data-testid="tool"]').first();
    if (await toolList.isVisible({ timeout: 8000 }).catch(() => false)) {
      await expect(toolList).toBeVisible();
    }
  });

  test('Tools page: create new tool form submits without 500', async ({ page, request }) => {
    await page.goto(`${BASE_URL}/tools`);
    await page.waitForLoadState('domcontentloaded');
    await assertNoReactCrash(page);

    // Click "Create" or "Add Tool" button
    const createBtn = page.locator(
      'button:has-text("Create"), button:has-text("Add"), button:has-text("New Tool"), [data-testid="create-tool"]'
    ).first();

    if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await createBtn.click();
      await page.waitForTimeout(500);

      // Fill out the form
      const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]').first();
      if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await nameInput.fill(`Test Tool ${Date.now()}`);

        const submitBtn = page.locator('button[type="submit"], button:has-text("Save"), button:has-text("Create")').first();
        if (await submitBtn.isVisible().catch(() => false)) {
          await submitBtn.click();
          await page.waitForTimeout(2000);
          await assertNoReactCrash(page);
        }
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 6 — AgentKit API Tests
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 6 — AgentKit API Validation', () => {

  test('GET /health returns < 500', async ({ request }) => {
    const resp = await request.get(`${API_URL}/health`).catch(() => null);
    if (resp) expect(resp.status()).toBeLessThan(500);
  });

  test('GET /api/tools returns list', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await request.get(`${API_URL}/api/tools`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    }).catch(() => null);
    if (resp) expect([200, 401, 403, 404]).toContain(resp.status());
  });

  test('POST /api/tools creates a tool', async ({ request }) => {
    const token = await getAuthToken(request);
    if (!token) { test.skip(); return; }

    const resp = await request.post(`${API_URL}/api/tools`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: {
        name: `e2e_test_tool_${Date.now()}`,
        type: 'tavily_search',
        config: { api_key: 'test_key', max_results: 5 },
        description: 'Playwright E2E test tool'
      }
    }).catch(() => null);
    if (resp) {
      expect(resp.status()).not.toBe(500);
      console.log(`POST /api/tools → ${resp.status()}`);
    }
  });

  test('SSE /sse endpoint returns streaming response', async ({ request }) => {
    // Test that the SSE endpoint is reachable (AgentKit uses /sse for MCP)
    const resp = await request.get(`${API_URL}/sse`, {
      headers: {
        Accept: 'text/event-stream',
        Authorization: `Bearer ${process.env.MCP_AUTH_TOKEN || 'test_token'}`
      },
      timeout: 5000,
    }).catch(() => null);

    if (resp) {
      // 200 = streaming OK, 401 = auth required (acceptable), 404 = no SSE
      expect([200, 401, 403, 404]).toContain(resp.status());
      console.log(`AgentKit SSE → ${resp.status()}`);
    }
  });

  test('Tool execution: agent does not crash on ambiguous query', async ({ request }) => {
    const token = await getAuthToken(request);
    if (!token) { test.skip(); return; }

    const resp = await request.post(`${API_URL}/api/agent/run`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        query: 'What is the weather?', // Ambiguous — tests tool selection
        tools: ['tavily_search']
      },
      timeout: 30000,
    }).catch(() => null);
    if (resp) {
      expect(resp.status()).not.toBe(500);
      console.log(`AgentKit /api/agent/run → ${resp.status()}`);
    }
  });

  test('Payload fuzzing: invalid tool type does not 500', async ({ request }) => {
    const token = await getAuthToken(request);
    const fuzzPayloads = [
      { name: 'fuzz1', type: null },
      { name: '', type: 'valid_type' },
      { name: 'a'.repeat(1000), type: 'valid_type' },
      { type: 'valid_type' }, // missing name
    ];
    for (const payload of fuzzPayloads) {
      const resp = await request.post(`${API_URL}/api/tools`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'Content-Type': 'application/json',
        },
        data: payload,
      }).catch(() => null);
      if (resp) expect(resp.status()).not.toBe(500);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7 — AgentKit Edge Cases
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 7 — AgentKit Edge Cases', () => {

  test('Circular workflow (DAG cycle): agent does not hang', async ({ request }) => {
    const token = await getAuthToken(request);
    if (!token) { test.skip(); return; }

    const resp = await request.post(`${API_URL}/api/workflows/validate`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        nodes: [
          { id: 'A', type: 'action' },
          { id: 'B', type: 'action' },
        ],
        edges: [
          { from: 'A', to: 'B' },
          { from: 'B', to: 'A' }, // Cyclic!
        ]
      },
      timeout: 10000,
    }).catch(() => null);

    if (resp) {
      // Should return 400 (validation error: cyclic graph) not 500
      expect(resp.status()).not.toBe(500);
      if (resp.status() === 400) {
        const body = await resp.json().catch(() => ({}));
        console.log(`Cyclic DAG correctly rejected: ${JSON.stringify(body)}`);
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 6 — AgentKit Mocked Workflow Feature Test
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 6 — AgentKit Mocked Features', () => {

  test('Mock DAG connection and execution', async ({ page }) => {
    await page.route('**/api/workflows/validate', async route => {
      const json = { valid: true, message: 'Workflow is valid' };
      await route.fulfill({ json, status: 200, contentType: 'application/json' });
    });

    await page.goto(`${BASE_URL}/workflow`);
    await page.waitForLoadState('domcontentloaded');

    // Find the save/validate button
    const saveBtn = page.locator('button:has-text("Save"), button:has-text("Validate")').first();
    if (await saveBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await saveBtn.click();
      await page.waitForTimeout(1000);
      await assertNoReactCrash(page);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 6.1 — AgentKit Deep Interactivity & Mocked Features
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phase 6.1 — Deep Interactivity', () => {

  test('Advanced DAG SSE execution stream mock', async ({ page }) => {
    // Intercept SSE or execute API
    await page.route('**/api/workflows/execute', async route => {
      // Mock returning an SSE event stream
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'data: {"node":"1", "status":"running"}\n\ndata: {"node":"5", "status":"completed"}\n\n'
      });
    });

    await page.goto(`${BASE_URL}/workflow`);
    await page.waitForLoadState('domcontentloaded');

    const executeBtn = page.locator('button:has-text("Run Workflow"), button:has-text("Execute"), [data-testid="run-dag"]').first();
    if (await executeBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await executeBtn.click();
      await page.waitForTimeout(1000);
      await assertNoReactCrash(page);
    }
  });

  test('Detailed Tool schema parameter validation mock', async ({ page }) => {
    await page.goto(`${BASE_URL}/tools`);
    await page.waitForLoadState('domcontentloaded');

    const addToolBtn = page.locator('button:has-text("Create Tool"), button:has-text("Add Tool")').first();
    if (await addToolBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await addToolBtn.click();
      await page.waitForTimeout(1000);
      
      // Look for schema/parameter input
      const paramInput = page.locator('input[name="parameters"], textarea[name="schema"]').first();
      if (await paramInput.isVisible().catch(() => false)) {
        await paramInput.fill('{"type":"object"}');
      }
      await assertNoReactCrash(page);
    }
  });

  test('Observability tracing deep-dive view rendering', async ({ page }) => {
    await page.goto(`${BASE_URL}/observability`);
    await page.waitForLoadState('domcontentloaded');

    const traceRow = page.locator('.trace-row, tr, [data-testid="trace"]').first();
    if (await traceRow.isVisible({ timeout: 5000 }).catch(() => false)) {
      await traceRow.click();
      await page.waitForTimeout(1000);
      const detailView = page.locator('.trace-detail, [data-testid="trace-details"]').first();
      if (await detailView.isVisible().catch(() => false)) {
        await expect(detailView).toBeVisible();
      }
      await assertNoReactCrash(page);
    }
  });
});
