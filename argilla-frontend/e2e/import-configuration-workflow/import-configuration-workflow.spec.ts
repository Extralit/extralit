import { test, expect } from '@playwright/test';
import { loginAndWaitFor } from '../common/login-and-wait-for';
import { mockImportHistoryAPI, mockDatasetAPI } from '../common/import-api-mock';

test.describe('Import Configuration Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses for import history and dataset creation
    await mockImportHistoryAPI(page);
    await mockDatasetAPI(page);

    // Login and navigate to home page
    await loginAndWaitFor(page, '/');
  });

  test('should navigate from Recent Imports to configuration page', async ({ page }) => {
    // Wait for Recent Imports section to load
    await expect(page.locator('.recent-imports')).toBeVisible();

    // Verify Recent Imports header is displayed
    await expect(page.locator('.recent-imports h3')).toContainText('Recent Imports');

    // Wait for import cards to load
    await expect(page.locator('.import-card').first()).toBeVisible();

    // Click on the first import record
    const firstImportCard = page.locator('.import-card').first();
    await expect(firstImportCard).toBeVisible();
    await firstImportCard.click();

    // Verify navigation to import configuration page
    await expect(page).toHaveURL(/\/new\/import\/[^\/]+$/);

    // Verify breadcrumb navigation
    await expect(page.locator('.breadcrumbs')).toBeVisible();
    await expect(page.locator('.breadcrumbs')).toContainText('Home');
    await expect(page.locator('.breadcrumbs')).toContainText('Import Configuration');
  });

  test('should load ImportHistory data and display in DatasetConfiguration', async ({ page }) => {
    // Navigate directly to import configuration page
    await page.goto('/new/import/test-import-123');

    // Wait for loading to complete
    await expect(page.locator('.loading-container')).toBeVisible();
    await expect(page.locator('.loading-text')).toContainText('Loading import configuration');

    // Wait for DatasetConfiguration component to load
    await expect(page.locator('.dataset-config')).toBeVisible();

    // Verify ImportHistory data preview is displayed instead of HuggingFace iframe
    await expect(page.locator('.import-history-data-preview')).toBeVisible();
    await expect(page.locator('iframe')).not.toBeVisible();

    // Verify import data table is displayed
    await expect(page.locator('.table-container')).toBeVisible();
    await expect(page.locator('.tabulator')).toBeVisible();

    // Verify preview header shows import information
    await expect(page.locator('.preview-header h3')).toContainText('test-papers.csv');
    await expect(page.locator('.preview-header .subtitle')).toContainText('references imported');
  });

  test('should display ImportHistory data in tabular format with proper columns', async ({ page }) => {
    await page.goto('/new/import/test-import-123');

    // Wait for data to load
    await expect(page.locator('.import-history-data-preview')).toBeVisible();
    await expect(page.locator('.tabulator')).toBeVisible();

    // Verify reference column is present and frozen
    await expect(page.locator('.tabulator-col[tabulator-field="reference"]')).toBeVisible();
    await expect(page.locator('.tabulator-col[tabulator-field="reference"]')).toHaveClass(/tabulator-frozen/);

    // Verify other expected columns from schema
    await expect(page.locator('.tabulator-col[tabulator-field="title"]')).toBeVisible();
    await expect(page.locator('.tabulator-col[tabulator-field="authors"]')).toBeVisible();
    await expect(page.locator('.tabulator-col[tabulator-field="doi"]')).toBeVisible();

    // Verify data rows are displayed
    await expect(page.locator('.tabulator-row')).toHaveCount(3); // Based on mock data

    // Verify first row contains expected data
    const firstRow = page.locator('.tabulator-row').first();
    await expect(firstRow.locator('.tabulator-cell[tabulator-field="reference"]')).toContainText('paper_001');
    await expect(firstRow.locator('.tabulator-cell[tabulator-field="title"]')).toContainText('Sample Paper Title 1');
  });

  test('should populate DatasetConfiguration fields from ImportHistory data', async ({ page }) => {
    await page.goto('/new/import/test-import-123');

    // Wait for configuration to load
    await expect(page.locator('.dataset-config')).toBeVisible();

    // Verify record preview is displayed in fields section
    await expect(page.locator('.dataset-config__fields .record')).toBeVisible();

    // Verify field mapping section is populated
    await expect(page.locator('.dataset-config__configuration')).toBeVisible();
    await expect(page.locator('.dataset-configuration-form')).toBeVisible();

    // Verify fields are created from ImportHistory schema
    await expect(page.locator('.field-selector')).toBeVisible();

    // Check that reference field is properly mapped
    const referenceField = page.locator('[data-field-name="reference"]');
    await expect(referenceField).toBeVisible();
  });

  test('should support dataset creation from ImportHistory data', async ({ page }) => {
    await page.goto('/new/import/test-import-123');

    // Wait for configuration to load
    await expect(page.locator('.dataset-config')).toBeVisible();

    // Configure dataset name
    const datasetNameInput = page.locator('input[name="dataset-name"]');
    await expect(datasetNameInput).toBeVisible();
    await datasetNameInput.fill('Test Import Dataset');

    // Add a question
    const addQuestionButton = page.locator('button:has-text("Add Question")');
    if (await addQuestionButton.isVisible()) {
      await addQuestionButton.click();

      // Configure question
      const questionTitleInput = page.locator('input[name="question-title"]');
      await questionTitleInput.fill('Quality Assessment');

      const questionTypeSelect = page.locator('select[name="question-type"]');
      await questionTypeSelect.selectOption('rating');
    }

    // Submit dataset creation
    const createButton = page.locator('button:has-text("Create Dataset")');
    await expect(createButton).toBeVisible();
    await createButton.click();

    // Verify dataset creation success
    await expect(page).toHaveURL(/\/dataset\/[^\/]+/);
    await expect(page.locator('.dataset-header')).toContainText('Test Import Dataset');
  });

  test('should handle ImportHistory data loading errors gracefully', async ({ page }) => {
    // Mock API to return error
    await page.route('**/api/v1/imports/history/invalid-import-id', route => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Import record not found' })
      });
    });

    await page.goto('/new/import/invalid-import-id');

    // Verify error state is displayed
    await expect(page.locator('.error-container')).toBeVisible();
    await expect(page.locator('.error-title')).toContainText('Failed to Load Import');
    await expect(page.locator('.error-message')).toContainText('Import record not found');

    // Verify retry and return home buttons are available
    await expect(page.locator('button:has-text("Retry")')).toBeVisible();
    await expect(page.locator('button:has-text("Return Home")')).toBeVisible();

    // Test return home functionality
    await page.locator('button:has-text("Return Home")').click();
    await expect(page).toHaveURL('/');
  });

  test('should handle network errors with retry mechanism', async ({ page }) => {
    let requestCount = 0;

    // Mock API to fail first two requests, succeed on third
    await page.route('**/api/v1/imports/history/test-import-123', route => {
      requestCount++;
      if (requestCount <= 2) {
        route.abort('failed');
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'test-import-123',
            filename: 'test-papers.csv',
            created_at: '2024-01-15T10:30:00Z',
            data: {
              data: [
                { reference: 'paper_001', title: 'Sample Paper Title 1', authors: 'Author 1', doi: '10.1000/test1' },
                { reference: 'paper_002', title: 'Sample Paper Title 2', authors: 'Author 2', doi: '10.1000/test2' }
              ],
              schema: {
                fields: [
                  { name: 'reference', type: 'string' },
                  { name: 'title', type: 'string' },
                  { name: 'authors', type: 'string' },
                  { name: 'doi', type: 'string' }
                ]
              }
            },
            metadata: {
              paper_001: { status: 'add' },
              paper_002: { status: 'add' }
            }
          })
        });
      }
    });

    await page.goto('/new/import/test-import-123');

    // Verify initial error state
    await expect(page.locator('.error-container')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('Network connection error');

    // Click retry button
    await page.locator('button:has-text("Retry")').click();

    // Verify still in error state after first retry
    await expect(page.locator('.error-container')).toBeVisible();

    // Click retry again
    await page.locator('button:has-text("Retry")').click();

    // Verify successful load after second retry
    await expect(page.locator('.dataset-config')).toBeVisible();
    await expect(page.locator('.import-history-data-preview')).toBeVisible();
  });

  test('should validate ImportHistory data structure and show appropriate errors', async ({ page }) => {
    // Mock API to return invalid data structure
    await page.route('**/api/v1/imports/history/empty-import-123', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'empty-import-123',
          filename: 'empty-import.csv',
          created_at: '2024-01-15T10:30:00Z',
          data: {
            data: [], // Empty data array
            schema: { fields: [] }
          },
          metadata: {}
        })
      });
    });

    await page.goto('/new/import/empty-import-123');

    // Verify error message for empty data
    await expect(page.locator('.error-container')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('This import contains no data to configure');
  });

  test('should populate record.metadata.reference from ImportHistory data', async ({ page }) => {
    await page.goto('/new/import/test-import-123');

    // Wait for configuration to load
    await expect(page.locator('.dataset-config')).toBeVisible();

    // Verify record preview shows reference field
    const recordPreview = page.locator('.dataset-config__fields .record');
    await expect(recordPreview).toBeVisible();

    // Check that reference field is populated in the record
    const referenceField = recordPreview.locator('[data-field="reference"]');
    await expect(referenceField).toBeVisible();
    await expect(referenceField).toContainText('paper_001');
  });

  test('should maintain existing DatasetConfiguration functionality with ImportHistory data', async ({ page }) => {
    await page.goto('/new/import/test-import-123');

    // Wait for configuration to load
    await expect(page.locator('.dataset-config')).toBeVisible();

    // Verify all main sections are present
    await expect(page.locator('.dataset-config__fields')).toBeVisible(); // Record preview
    await expect(page.locator('.dataset-config__questions-wrapper')).toBeVisible(); // Questions section
    await expect(page.locator('.dataset-config__preview')).toBeVisible(); // Data preview
    await expect(page.locator('.dataset-config__configuration')).toBeVisible(); // Configuration form

    // Verify resizable panels work
    const horizontalResizer = page.locator('.resizable-h__handle');
    const verticalResizer = page.locator('.resizable-v__handle');

    await expect(horizontalResizer).toBeVisible();
    await expect(verticalResizer).toBeVisible();

    // Test field mapping functionality
    const fieldSelector = page.locator('.field-selector');
    if (await fieldSelector.isVisible()) {
      // Verify field options are available from ImportHistory schema
      await expect(fieldSelector.locator('option[value="title"]')).toBeVisible();
      await expect(fieldSelector.locator('option[value="authors"]')).toBeVisible();
      await expect(fieldSelector.locator('option[value="doi"]')).toBeVisible();
    }
  });

  test('should handle subset changes in ImportHistory configuration', async ({ page }) => {
    await page.goto('/new/import/test-import-123');

    // Wait for configuration to load
    await expect(page.locator('.dataset-config')).toBeVisible();

    // Look for subset selector if available
    const subsetSelector = page.locator('select[name="subset"]');
    if (await subsetSelector.isVisible()) {
      // Test subset change
      await subsetSelector.selectOption('default');

      // Verify data preview updates
      await expect(page.locator('.import-history-data-preview')).toBeVisible();
    }
  });

  test('should support row selection in ImportHistory data preview', async ({ page }) => {
    await page.goto('/new/import/test-import-123');

    // Wait for data preview to load
    await expect(page.locator('.import-history-data-preview')).toBeVisible();
    await expect(page.locator('.tabulator-row')).toHaveCount(3);

    // Click on first row
    const firstRow = page.locator('.tabulator-row').first();
    await firstRow.click();

    // Verify row selection (this would typically update the record preview)
    // The exact behavior depends on the implementation
    await expect(firstRow).toHaveClass(/tabulator-selected/);
  });

  test('should handle browser navigation correctly', async ({ page }) => {
    // Start from home page
    await page.goto('/');
    await expect(page.locator('.recent-imports')).toBeVisible();

    // Navigate to import configuration
    await page.locator('.import-card').first().click();
    await expect(page).toHaveURL(/\/new\/import\/[^\/]+$/);

    // Use browser back button
    await page.goBack();
    await expect(page).toHaveURL('/');
    await expect(page.locator('.recent-imports')).toBeVisible();

    // Use browser forward button
    await page.goForward();
    await expect(page).toHaveURL(/\/new\/import\/[^\/]+$/);
    await expect(page.locator('.dataset-config')).toBeVisible();
  });

  test('should handle direct URL access to import configuration', async ({ page }) => {
    // Navigate directly to import configuration URL
    await page.goto('/new/import/test-import-123');

    // Verify page loads correctly
    await expect(page.locator('.dataset-config')).toBeVisible();
    await expect(page.locator('.import-history-data-preview')).toBeVisible();

    // Verify breadcrumbs work for direct access
    await expect(page.locator('.breadcrumbs')).toBeVisible();

    // Test breadcrumb navigation
    await page.locator('.breadcrumbs a:has-text("Home")').click();
    await expect(page).toHaveURL('/');
  });
});