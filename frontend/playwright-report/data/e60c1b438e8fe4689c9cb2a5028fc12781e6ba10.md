# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: agentkit_operations.spec.ts >> Phase 6 — AgentKit Operations >> All main navigation pages render without crash
- Location: e2e/agentkit_operations.spec.ts:34:3

# Error details

```
Error: page.goto: net::ERR_NAME_NOT_RESOLVED at https://connect/
Call log:
  - navigating to "https://connect/", waiting until "load"

```

# Test source

```ts
  1   | import { test, expect, Page } from '@playwright/test';
  2   | 
  3   | /**
  4   |  * AgentKit — Comprehensive E2E Suite
  5   |  * Phase 6: Agent Operations (React Flow DAGs, Tool Config)
  6   |  * Phase 6: Extended UI/UX Validation
  7   |  * Phase 7: Deep Component Integration
  8   |  */
  9   | 
  10  | const BASE_URL = process.env.AGENTKIT_URL    || process.env.TEST_BASE_URL || '/';
  11  | const API_URL  = process.env.AGENTKIT_API_URL || '/';
  12  | const AUTH_URL = process.env.INTELAI_API_URL  || '/';
  13  | 
  14  | async function assertNoReactCrash(page: Page) {
  15  |   await expect(page.locator('text=/An unexpected error occurred|Something went wrong/i')).toHaveCount(0);
  16  | }
  17  | 
  18  | async function getAuthToken(request: any): Promise<string> {
  19  |   const resp = await request.post(`${AUTH_URL}/api/login`, {
  20  |     data: { username: 'admin', password: process.env.ADMIN_PASS || '' }
  21  |   }).catch(() => null);
  22  |   if (resp && resp.ok()) {
  23  |     const body = await resp.json();
  24  |     return body.access_token || body.token || '';
  25  |   }
  26  |   return '';
  27  | }
  28  | 
  29  | // ─────────────────────────────────────────────────────────────────────────────
  30  | // Phase 6 — AgentKit UI Workflows
  31  | // ─────────────────────────────────────────────────────────────────────────────
  32  | test.describe('Phase 6 — AgentKit Operations', () => {
  33  | 
  34  |   test('All main navigation pages render without crash', async ({ page }) => {
  35  |     await page.goto(`${BASE_URL}/`);
  36  |     const routes = [
  37  |       '/connect', '/intelligence', '/observability',
  38  |       '/overview', '/resources', '/tools', '/workflow'
  39  |     ];
  40  |     for (const route of routes) {
> 41  |       await page.goto(`${'/'}${route}`);
      |                  ^ Error: page.goto: net::ERR_NAME_NOT_RESOLVED at https://connect/
  42  |       await page.waitForLoadState('domcontentloaded');
  43  |       await assertNoReactCrash(page);
  44  |       console.log(`✅ AgentKit ${route} — OK`);
  45  |     }
  46  |   });
  47  | 
  48  |   test('Workflow Builder: React Flow DAG canvas renders', async ({ page }) => {
  49  |     await page.goto(`${BASE_URL}/workflow`);
  50  |     await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  51  |     await assertNoReactCrash(page);
  52  | 
  53  |     // React Flow renders as SVG with class "react-flow"
  54  |     const canvas = page.locator('.react-flow, canvas, svg, [data-testid="workflow"]').first();
  55  |     if (await canvas.isVisible({ timeout: 8000 }).catch(() => false)) {
  56  |       await expect(canvas).toBeVisible();
  57  |       console.log('✅ React Flow DAG canvas visible');
  58  |     }
  59  |   });
  60  | 
  61  |   test('Workflow Builder: DAG nodes are draggable', async ({ page }) => {
  62  |     await page.goto(`${BASE_URL}/workflow`);
  63  |     await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  64  |     await assertNoReactCrash(page);
  65  | 
  66  |     // Find a React Flow node and drag it
  67  |     const node = page.locator('.react-flow__node, [data-testid="node"]').first();
  68  |     if (await node.isVisible({ timeout: 5000 }).catch(() => false)) {
  69  |       const box = await node.boundingBox();
  70  |       if (box) {
  71  |         await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  72  |         await page.mouse.down();
  73  |         await page.mouse.move(box.x + 100, box.y + 50);
  74  |         await page.mouse.up();
  75  |         await page.waitForTimeout(500);
  76  |         await assertNoReactCrash(page);
  77  |         console.log('✅ DAG node dragged successfully');
  78  |       }
  79  |     }
  80  |   });
  81  | 
  82  |   test('Tools page: tool list renders', async ({ page }) => {
  83  |     await page.goto(`${BASE_URL}/tools`);
  84  |     await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  85  |     await assertNoReactCrash(page);
  86  |     const toolList = page.locator('table, .tool-list, .tool-card, [data-testid="tool"]').first();
  87  |     if (await toolList.isVisible({ timeout: 8000 }).catch(() => false)) {
  88  |       await expect(toolList).toBeVisible();
  89  |     }
  90  |   });
  91  | 
  92  |   test('Tools page: create new tool form submits without 500', async ({ page, request }) => {
  93  |     await page.goto(`${BASE_URL}/tools`);
  94  |     await page.waitForLoadState('domcontentloaded');
  95  |     await assertNoReactCrash(page);
  96  | 
  97  |     // Click "Create" or "Add Tool" button
  98  |     const createBtn = page.locator(
  99  |       'button:has-text("Create"), button:has-text("Add"), button:has-text("New Tool"), [data-testid="create-tool"]'
  100 |     ).first();
  101 | 
  102 |     if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
  103 |       await createBtn.click();
  104 |       await page.waitForTimeout(500);
  105 | 
  106 |       // Fill out the form
  107 |       const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]').first();
  108 |       if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
  109 |         await nameInput.fill(`Test Tool ${Date.now()}`);
  110 | 
  111 |         const submitBtn = page.locator('button[type="submit"], button:has-text("Save"), button:has-text("Create")').first();
  112 |         if (await submitBtn.isVisible().catch(() => false)) {
  113 |           await submitBtn.click();
  114 |           await page.waitForTimeout(2000);
  115 |           await assertNoReactCrash(page);
  116 |         }
  117 |       }
  118 |     }
  119 |   });
  120 | });
  121 | 
  122 | // ─────────────────────────────────────────────────────────────────────────────
  123 | // Phase 6 — AgentKit API Tests
  124 | // ─────────────────────────────────────────────────────────────────────────────
  125 | test.describe('Phase 6 — AgentKit API Validation', () => {
  126 | 
  127 |   test('GET /health returns < 500', async ({ request }) => {
  128 |     const resp = await request.get(`${API_URL}/health`).catch(() => null);
  129 |     if (resp) expect(resp.status()).toBeLessThan(500);
  130 |   });
  131 | 
  132 |   test('GET /api/tools returns list', async ({ request }) => {
  133 |     const token = await getAuthToken(request);
  134 |     const resp = await request.get(`${API_URL}/api/tools`, {
  135 |       headers: token ? { Authorization: `Bearer ${token}` } : {}
  136 |     }).catch(() => null);
  137 |     if (resp) expect([200, 401, 403, 404]).toContain(resp.status());
  138 |   });
  139 | 
  140 |   test('POST /api/tools creates a tool', async ({ request }) => {
  141 |     const token = await getAuthToken(request);
```