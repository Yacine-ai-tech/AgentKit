import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:5173';

test.describe('Phase 5: AgentKit Operations & Automation', () => {

  test('Slice 5.1: Agent Workspace & DAG Workflows', async ({ page }) => {
    // 1. Overview Dashboard
    await page.goto(`${BASE_URL}/`);
    await expect(page.locator('text=/AgentKit/i').first()).toBeVisible();
    await expect(page.locator('.kpi-grid, .agent-stats, canvas, svg').first()).toBeVisible({ timeout: 10000 });

    // 2. Workflow Builder / DAG
    await page.goto(`${BASE_URL}/workflow`);
    await expect(page.locator('text=/Workflow/i').first()).toBeVisible();
    
    // Assert the presence of the drag-and-drop workflow canvas or nodes
    const workflowCanvas = page.locator('.react-flow, .workflow-canvas, canvas, svg, .node');
    await expect(workflowCanvas.first()).toBeVisible({ timeout: 10000 });
  });

  test('Slice 5.1: Tools Configuration & Intelligence Mapping', async ({ page }) => {
    // 1. Tools Page
    await page.goto(`${BASE_URL}/tools`);
    await expect(page.locator('text=/Tools/i').first()).toBeVisible();
    
    // Check if tools configuration grids or API keys inputs are rendered
    const toolCards = page.locator('.card, .grid, form');
    await expect(toolCards.first()).toBeVisible();

    // 2. Intelligence Page
    await page.goto(`${BASE_URL}/intelligence`);
    await expect(page.locator('text=/Intelligence/i').first()).toBeVisible();
    
    // Verify LLM model selection or reasoning config renders
    const selectOrInput = page.locator('select, input, .combo-box, [role="combobox"]');
    await expect(selectOrInput.first()).toBeVisible();
  });

  test('Slice 5.1: Observability & System Resources', async ({ page }) => {
    const monitoringPages = [
      { path: '/observability', title: 'Observability' },
      { path: '/resources', title: 'Resources' },
      { path: '/connect', title: 'Connect' }
    ];

    for (const mp of monitoringPages) {
      await test.step(`Verify ${mp.title} Rendering`, async () => {
        await page.goto(`${BASE_URL}${mp.path}`);
        await expect(page.locator('body')).toBeVisible();
        await expect(page.locator(`text=/${mp.title}/i`).first()).toBeVisible({ timeout: 5000 });
        
        // Dashboards usually contain lists, tables, or generic layout wrappers
        const layoutContainers = page.locator('div');
        await expect(layoutContainers.first()).toBeVisible();
        
        // Ensure no fatal React crashes
        await expect(page.locator('text=/An unexpected error occurred/i')).toHaveCount(0);
      });
    }
  });

});
