import { Page } from "@playwright/test";

export async function mockImportHistoryAPI(page: Page) {
  // Mock recent imports list
  await page.route("**/api/v1/imports/history?*", (route) => {
    const url = new URL(route.request().url());
    const limit = url.searchParams.get("size") || "10";
    const workspaceId = url.searchParams.get("workspace_id");

    if (!workspaceId) {
      route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "workspace_id is required" }),
      });
      return;
    }

    const mockRecentImports = {
      items: [
        {
          id: "test-import-123",
          workspace_id: workspaceId,
          user_id: "user-123",
          filename: "test-papers.csv",
          created_at: "2024-01-15T10:30:00Z",
          metadata: {
            total_documents: 150,
            add_count: 145,
            update_count: 3,
            skip_count: 1,
            failed_count: 1,
          },
        },
        {
          id: "test-import-456",
          workspace_id: workspaceId,
          user_id: "user-123",
          filename: "research-papers-batch2.csv",
          created_at: "2024-01-14T15:45:00Z",
          metadata: {
            total_documents: 89,
            add_count: 87,
            update_count: 2,
            skip_count: 0,
            failed_count: 0,
          },
        },
        {
          id: "test-import-789",
          workspace_id: workspaceId,
          user_id: "user-123",
          filename: "literature-review.csv",
          created_at: "2024-01-13T09:15:00Z",
          metadata: {
            total_documents: 234,
            add_count: 230,
            update_count: 4,
            skip_count: 0,
            failed_count: 0,
          },
        },
      ].slice(0, parseInt(limit)),
      total: 3,
      page: 1,
      size: parseInt(limit),
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockRecentImports),
    });
  });

  // Mock import history details
  await page.route("**/api/v1/imports/history/test-import-123", (route) => {
    const mockImportDetails = {
      id: "test-import-123",
      workspace_id: "workspace-123",
      user_id: "user-123",
      filename: "test-papers.csv",
      created_at: "2024-01-15T10:30:00Z",
      data: {
        data: [
          {
            reference: "paper_001",
            title: "Sample Paper Title 1",
            authors: "Author 1, Co-Author 1",
            doi: "10.1000/test1",
            year: 2023,
            journal: "Test Journal 1",
            abstract: "This is a sample abstract for paper 1...",
            keywords: "machine learning, AI, test",
            url: "https://example.com/paper1",
          },
          {
            reference: "paper_002",
            title: "Sample Paper Title 2",
            authors: "Author 2, Co-Author 2",
            doi: "10.1000/test2",
            year: 2023,
            journal: "Test Journal 2",
            abstract: "This is a sample abstract for paper 2...",
            keywords: "deep learning, neural networks",
            url: "https://example.com/paper2",
          },
          {
            reference: "paper_003",
            title: "Sample Paper Title 3",
            authors: "Author 3",
            doi: "10.1000/test3",
            year: 2024,
            journal: "Test Journal 3",
            abstract: "This is a sample abstract for paper 3...",
            keywords: "natural language processing, NLP",
            url: "https://example.com/paper3",
          },
        ],
        schema: {
          fields: [
            { name: "reference", type: "string", required: true },
            { name: "title", type: "string", required: true },
            { name: "authors", type: "string", required: false },
            { name: "doi", type: "string", required: false },
            { name: "year", type: "integer", required: false },
            { name: "journal", type: "string", required: false },
            { name: "abstract", type: "text", required: false },
            { name: "keywords", type: "string", required: false },
            { name: "url", type: "string", required: false },
          ],
        },
      },
      metadata: {
        paper_001: { status: "add", processed_at: "2024-01-15T10:30:15Z" },
        paper_002: { status: "add", processed_at: "2024-01-15T10:30:16Z" },
        paper_003: { status: "add", processed_at: "2024-01-15T10:30:17Z" },
      },
      summary: {
        total_documents: 3,
        add_count: 3,
        update_count: 0,
        skip_count: 0,
        failed_count: 0,
      },
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockImportDetails),
    });
  });

  // Mock other import details for different test scenarios
  await page.route("**/api/v1/imports/history/test-import-456", (route) => {
    const mockImportDetails = {
      id: "test-import-456",
      workspace_id: "workspace-123",
      user_id: "user-123",
      filename: "research-papers-batch2.csv",
      created_at: "2024-01-14T15:45:00Z",
      data: {
        data: [
          {
            reference: "batch2_001",
            title: "Research Paper Batch 2 - Paper 1",
            authors: "Researcher A, Researcher B",
            doi: "10.1000/batch2-1",
            year: 2023,
            journal: "Research Journal A",
          },
          {
            reference: "batch2_002",
            title: "Research Paper Batch 2 - Paper 2",
            authors: "Researcher C",
            doi: "10.1000/batch2-2",
            year: 2024,
            journal: "Research Journal B",
          },
        ],
        schema: {
          fields: [
            { name: "reference", type: "string", required: true },
            { name: "title", type: "string", required: true },
            { name: "authors", type: "string", required: false },
            { name: "doi", type: "string", required: false },
            { name: "year", type: "integer", required: false },
            { name: "journal", type: "string", required: false },
          ],
        },
      },
      metadata: {
        batch2_001: { status: "add" },
        batch2_002: { status: "update" },
      },
      summary: {
        total_documents: 2,
        add_count: 1,
        update_count: 1,
        skip_count: 0,
        failed_count: 0,
      },
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockImportDetails),
    });
  });

  // Mock import history details for third import
  await page.route("**/api/v1/imports/history/test-import-789", (route) => {
    const mockImportDetails = {
      id: "test-import-789",
      workspace_id: "workspace-123",
      user_id: "user-123",
      filename: "literature-review.csv",
      created_at: "2024-01-13T09:15:00Z",
      data: {
        data: [
          {
            reference: "lit_001",
            title: "Literature Review Paper 1",
            authors: "Review Author 1",
            doi: "10.1000/lit-1",
            year: 2023,
            journal: "Review Journal",
          },
        ],
        schema: {
          fields: [
            { name: "reference", type: "string", required: true },
            { name: "title", type: "string", required: true },
            { name: "authors", type: "string", required: false },
            { name: "doi", type: "string", required: false },
            { name: "year", type: "integer", required: false },
            { name: "journal", type: "string", required: false },
          ],
        },
      },
      metadata: {
        lit_001: { status: "add" },
      },
      summary: {
        total_documents: 1,
        add_count: 1,
        update_count: 0,
        skip_count: 0,
        failed_count: 0,
      },
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockImportDetails),
    });
  });
}

export async function mockDatasetAPI(page: Page) {
  // Mock dataset creation endpoint
  await page.route("**/api/v1/datasets", (route) => {
    if (route.request().method() === "POST") {
      const mockDataset = {
        id: "dataset-123",
        name: "Test Import Dataset",
        workspace_id: "workspace-123",
        created_at: "2024-01-15T11:00:00Z",
        updated_at: "2024-01-15T11:00:00Z",
        status: "ready",
        fields: [],
        questions: [],
        records_count: 0,
      };

      route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(mockDataset),
      });
    } else {
      route.continue();
    }
  });

  // Mock dataset details endpoint
  await page.route("**/api/v1/datasets/dataset-123", (route) => {
    const mockDataset = {
      id: "dataset-123",
      name: "Test Import Dataset",
      workspace_id: "workspace-123",
      created_at: "2024-01-15T11:00:00Z",
      updated_at: "2024-01-15T11:00:00Z",
      status: "ready",
      fields: [
        {
          id: "field-1",
          name: "reference",
          title: "Reference",
          type: "text",
          required: true,
        },
        {
          id: "field-2",
          name: "title",
          title: "Title",
          type: "text",
          required: true,
        },
      ],
      questions: [
        {
          id: "question-1",
          name: "quality_assessment",
          title: "Quality Assessment",
          type: "rating",
          required: false,
          settings: {
            options: [
              { value: 1, text: "Poor" },
              { value: 2, text: "Fair" },
              { value: 3, text: "Good" },
              { value: 4, text: "Excellent" },
            ],
          },
        },
      ],
      records_count: 3,
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockDataset),
    });
  });

  // Mock workspace datasets endpoint
  await page.route("**/api/v1/workspaces/*/datasets*", (route) => {
    const mockDatasets = {
      items: [
        {
          id: "dataset-123",
          name: "Test Import Dataset",
          workspace_id: "workspace-123",
          created_at: "2024-01-15T11:00:00Z",
          status: "ready",
          records_count: 3,
        },
      ],
      total: 1,
      page: 1,
      size: 50,
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockDatasets),
    });
  });

  // Mock fields endpoint for dataset configuration
  await page.route("**/api/v1/fields*", (route) => {
    const mockFields = {
      items: [
        {
          id: "field-1",
          name: "reference",
          title: "Reference",
          type: "text",
          required: true,
        },
        {
          id: "field-2",
          name: "title",
          title: "Title",
          type: "text",
          required: true,
        },
        {
          id: "field-3",
          name: "authors",
          title: "Authors",
          type: "text",
          required: false,
        },
      ],
      total: 3,
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockFields),
    });
  });

  // Mock questions endpoint for dataset configuration
  await page.route("**/api/v1/questions*", (route) => {
    const mockQuestions = {
      items: [
        {
          id: "question-1",
          name: "quality_assessment",
          title: "Quality Assessment",
          type: "rating",
          required: false,
          settings: {
            options: [
              { value: 1, text: "Poor" },
              { value: 2, text: "Fair" },
              { value: 3, text: "Good" },
              { value: 4, text: "Excellent" },
            ],
          },
        },
      ],
      total: 1,
    };

    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockQuestions),
    });
  });
}
