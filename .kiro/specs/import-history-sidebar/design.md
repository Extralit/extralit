# Design Document

## Overview

The Import History Sidebar feature enhances the home page user experience by replacing the example datasets section with a "Recent Imports" section that displays the 5 most recent ImportHistory records for the selected workspace. Users can click on these records to navigate to a new route (`new/import/{import_id}`) that displays the DatasetConfiguration component populated with ImportHistory data instead of HuggingFace Hub data.

This feature builds on the existing papers-library-importer functionality and reuses the existing DatasetConfiguration component architecture, adapting it to work with ImportHistory data structures. The design follows the established patterns in the codebase: Vue.js components with TypeScript, domain-driven architecture with use cases and repositories, and consistent styling using the existing design system.

## Architecture

### High-Level Flow

1. **Home Page Load**: User visits home page, Recent Imports section loads automatically for selected workspace
2. **Import History Display**: System fetches and displays 5 most recent ImportHistory records with summary information
3. **Navigation**: User clicks on ImportHistory record, navigates to `new/import/{import_id}` route
4. **Import Configuration Load**: System fetches detailed ImportHistory data and populates DatasetConfiguration component
5. **Data Preview**: ImportHistory tabular data displays in preview section instead of HuggingFace iframe
6. **Dataset Configuration**: User configures fields and questions using existing DatasetConfiguration workflow
7. **Dataset Creation**: System creates dataset from ImportHistory data with user's configuration

### Component Interaction

```mermaid
graph TD
    A[Home Page] --> B[Recent Imports Sidebar]
    B --> C[ImportHistory API]
    C --> D[ImportHistory List Display]
    D --> E[User Clicks Import Record]
    E --> F[Navigate to /new/import/{import_id}]
    F --> G[Import Configuration Page]
    G --> H[Fetch ImportHistory Details]
    H --> I[ImportHistory Details API]
    I --> J[DatasetConfiguration Component]
    J --> K[ImportHistory Data Preview]
    J --> L[Field Mapping Configuration]
    L --> M[Dataset Creation]
    M --> N[Dataset Created with ImportHistory Data]
```

## Components and Interfaces

### Backend Components

#### 1. ImportHistory API (Already Implemented)

**Existing Endpoints:**
- `GET /api/v1/imports/history` - List import histories for workspace (supports workspace_id parameter)
- `GET /api/v1/imports/history/{history_id}` - Get detailed ImportHistory record with full data

**Enhancement Needed:**
- Add support for `limit` parameter to existing list endpoint for Recent Imports sidebar

**Existing Functionality:**
- Returns complete ImportHistory record including full `data` field in detailed view
- Validates user access to the ImportHistory record's workspace
- Provides detailed tabular data for DatasetConfiguration component
- List view includes metadata but excludes data for performance

#### 2. ImportHistory Context Enhancement (`extralit-server/src/argilla_server/contexts/imports.py`)

**New Services:**
- `get_import_history_details()` - Retrieve complete ImportHistory record with data
- `get_recent_import_history()` - Get limited list of recent imports for sidebar

### Frontend Components

#### 1. Home Page Integration (`argilla-frontend/pages/index.vue`)

**Recent Imports Sidebar Section:**
- Replace example datasets section with Recent Imports component
- Display 5 most recent ImportHistory records for selected workspace
- Show loading states and empty states appropriately
- Integrate with existing workspace selection functionality
- Add "View All Imports" button below recent imports list
- Add "Import Documents" button to open ImportModal

**Modified Structure:**
```vue
<template v-slot:page-sidebar>
  <div class="home__sidebar__buttons">
    <ImportDocuments @on-click="openImportModal" />
    <!-- Other import buttons -->
  </div>
  <BaseSeparator class="home__sidebar__separator" />
  <div class="home__sidebar__content">
    <RecentImports
      :workspace="selectedWorkspace"
      @import-selected="navigateToImportConfig"
      @view-all-imports="openImportHistoryModal"
      @import-documents="openImportModal"
    />
  </div>
</template>
```

#### 2. Recent Imports Component (`argilla-frontend/components/features/import/RecentImports.vue`)

**Features:**
- Displays 5 most recent ImportHistory records for the workspace
- Shows filename, import date, and summary statistics
- Handles loading and empty states
- Provides click navigation to import configuration
- Responsive design for sidebar display

**Component Structure:**
```vue
<template>
  <div class="recent-imports">
    <div class="recent-imports__header">
      <h3>Recent Imports</h3>
      <p class="subtitle">Configure datasets from your recent imports</p>
    </div>

    <div v-if="isLoading" class="loading-state">
      <BaseSpinner />
      <p>Loading recent imports...</p>
    </div>

    <div v-else-if="!imports.length" class="empty-state">
      <BaseIcon icon-name="document" />
      <p>No recent imports found</p>
      <p class="hint">Import documents to get started</p>
    </div>

    <div v-else class="imports-list">
      <RecentImportCard
        v-for="importRecord in imports"
        :key="importRecord.id"
        :import-record="importRecord"
        @click="$emit('import-selected', importRecord)"
      />
    </div>

    <div class="imports-actions">
      <BaseButton
        variant="outline"
        @click="$emit('view-all-imports')"
        class="view-all-btn"
      >
        View All Imports
      </BaseButton>
      <BaseButton
        variant="primary"
        @click="$emit('import-documents')"
        class="import-btn"
      >
        Import Documents
      </BaseButton>
    </div>
  </div>
</template>
```

#### 3. Recent Import Card Component (`argilla-frontend/components/features/import/RecentImportCard.vue`)

**Features:**
- Compact card display for individual ImportHistory records
- Shows filename, date, and summary statistics
- Hover states and click interactions
- Consistent styling with existing card components

**Card Structure:**
```vue
<template>
  <div class="import-card" @click="$emit('click')">
    <div class="import-card__header">
      <h4 class="filename">{{ importRecord.filename }}</h4>
      <span class="date">{{ formatDate(importRecord.created_at) }}</span>
    </div>
    <div class="import-card__stats">
      <div class="stat">
        <span class="count">{{ totalPapers }}</span>
        <span class="label">papers</span>
      </div>
      <div class="stat success">
        <span class="count">{{ successCount }}</span>
        <span class="label">success</span>
      </div>
      <div class="stat failed" v-if="failedCount > 0">
        <span class="count">{{ failedCount }}</span>
        <span class="label">failed</span>
      </div>
    </div>
  </div>
</template>
```

#### 4. Import Configuration Page (`argilla-frontend/pages/new/import/_id.vue`)

**Features:**
- New page route for ImportHistory-based dataset configuration
- Fetches ImportHistory details using route parameter
- Renders DatasetConfiguration component with ImportHistory data
- Handles loading, error, and navigation states
- Provides breadcrumb navigation

**Page Structure:**
```vue
<template>
  <div class="import-config-page">
    <AppHeader
      :breadcrumbs="breadcrumbs"
      @breadcrumb-action="handleBreadcrumbAction"
    />

    <div v-if="isLoading" class="loading-container">
      <BaseSpinner />
      <p>Loading import configuration...</p>
    </div>

    <div v-else-if="error" class="error-container">
      <BaseIcon icon-name="danger" />
      <h3>Failed to Load Import</h3>
      <p>{{ error }}</p>
      <BaseButton @click="retry">Retry</BaseButton>
      <BaseButton variant="outline" @click="goHome">Return Home</BaseButton>
    </div>

    <DatasetConfiguration
      v-else-if="dataset"
      :dataset="dataset"
      @change-subset="handleSubsetChange"
    />
  </div>
</template>
```

#### 5. ImportHistory Dataset Creation Builder (`argilla-frontend/v1/domain/entities/import/ImportHistoryDatasetBuilder.ts`)

**Purpose:**
- Adapts ImportHistory data structure to DatasetCreation format
- Converts ImportHistory tabular data to dataset fields and records
- Provides field mapping capabilities similar to HuggingFace datasets
- Handles data type inference and validation

**Class Structure:**
```typescript
export class ImportHistoryDatasetBuilder {
  private readonly importHistoryData: ImportHistoryDetailsResponse;
  private readonly datasetName: string;

  constructor(importHistoryData: ImportHistoryDetailsResponse) {
    this.importHistoryData = importHistoryData;
    this.datasetName = this.generateDatasetName();
  }

  build(): DatasetCreation {
    const subset = this.createSubsetFromImportHistory();
    return new DatasetCreation(
      this.importHistoryData.id,
      this.datasetName,
      [subset]
    );
  }

  private createSubsetFromImportHistory(): Subset {
    const features = this.extractFeaturesFromSchema();
    return new Subset("default", { features });
  }

  private extractFeaturesFromSchema(): Record<string, Feature> {
    // Convert ImportHistory schema fields to DatasetCreation features
  }
}
```

#### 6. Enhanced ImportHistory Use Cases

**New Get ImportHistory Details Use Case (`argilla-frontend/v1/domain/usecases/get-import-history-details-use-case.ts`)**
```typescript
export class GetImportHistoryDetailsUseCase {
  constructor(private readonly axios: NuxtAxiosInstance) {}

  async execute(importId: string): Promise<ImportHistoryResponse> {
    const response = await this.axios.get(`/v1/imports/history/${importId}`);
    return response.data;
  }
}
```

**Enhanced Existing GetImportHistoryUseCase (add recent imports method)**
```typescript
export class GetImportHistoryUseCase {
  constructor(private readonly axios: NuxtAxiosInstance) {}

  // Existing method for full history with pagination
  async execute(params: ImportHistoryListParams): Promise<ImportHistoryListResponse> {
    // Existing implementation
  }

  // New method for recent imports
  async getRecent(workspaceId: string, limit: number = 5): Promise<ImportHistoryListResponse> {
    const params: ImportHistoryListParams = {
      size: limit,
      sort_by: 'created_at',
      sort_order: 'desc',
      filters: { workspace_id: workspaceId }
    };
    return await this.execute(params);
  }
}
```

### API Schemas

#### Existing API Schemas (Already Implemented)
The `ImportHistoryResponse` schema already exists and supports both list and detailed views:
- List view: includes `id`, `workspace_id`, `user_id`, `filename`, `created_at`, `metadata` (excludes `data`)
- Detailed view: includes all fields including `data` with complete tabular dataframe

#### Enhanced ImportHistory List Parameters
The existing `GET /api/v1/imports/history` endpoint will be enhanced to support:
- `limit` parameter for Recent Imports sidebar (default: 5)
- Existing `workspace_id`, `page`, `size`, `sort_by`, `sort_order` parameters
- No new request models needed - reuse existing query parameters

### Data Flow Integration

#### ImportHistory to DatasetConfiguration Integration

The ImportHistoryDatasetBuilder handles conversion from ImportHistory data structure to DatasetCreation format, enabling seamless integration with the existing DatasetConfiguration component. Key mappings include ImportHistory schema fields to DatasetCreation features, and automatic population of `record.metadata.reference` from ImportHistory data.

#### DatasetConfiguration Component Enhancement

The existing DatasetConfiguration component will be enhanced to support ImportHistory data by adding conditional rendering in the preview section. When ImportHistory data is provided, the component will display ImportHistoryDataPreview instead of the HuggingFace Hub iframe, while maintaining all existing functionality for field mapping and dataset creation.

#### ImportHistory Data Preview Component

A new component that displays ImportHistory tabular data using BaseSimpleTable with search, filtering, and pagination capabilities. This component replaces the HuggingFace Hub iframe when working with ImportHistory data in the DatasetConfiguration component.

## Error Handling

### ImportHistory Loading Errors
- Invalid import ID: Redirect to home with error message
- Access denied: Show authorization error with login option
- Network failures: Provide retry mechanism with exponential backoff
- Data corruption: Display error details and suggest re-import

### DatasetConfiguration Errors
- Missing ImportHistory data: Show loading state until data arrives
- Invalid data structure: Display validation errors with guidance
- Field mapping conflicts: Highlight problematic mappings with suggestions
- Dataset creation failures: Show detailed error messages with retry options

### User Experience
- Loading states for all async operations
- Progressive enhancement with skeleton screens
- Graceful degradation for network issues
- Clear error messages with actionable guidance

## Testing Strategy

### Unit Tests
- ImportHistory data transformation logic
- DatasetConfiguration component with ImportHistory data
- Recent Imports component display and interactions
- API response handling and error scenarios

### Integration Tests
- End-to-end navigation from home page to import configuration
- ImportHistory API integration with frontend components
- DatasetConfiguration workflow with ImportHistory data
- Error handling across component boundaries

### Performance Tests
- Large ImportHistory dataset handling
- Recent Imports sidebar loading performance
- DatasetConfiguration rendering with large datasets
- Memory usage with multiple ImportHistory records

## Implementation Structure

### File Organization
```
argilla-frontend/
├── pages/new/import/
│   └── _id.vue                        # Import configuration page
├── components/features/import/
│   ├── RecentImports.vue              # Recent imports sidebar component
│   ├── RecentImportCard.vue           # Individual import card
│   ├── ImportHistoryDataPreview.vue   # Data preview for configuration
│   └── useRecentImportsViewModel.ts   # Recent imports view model
├── v1/domain/
│   ├── entities/import/
│   │   ├── ImportHistoryDatasetBuilder.ts # ImportHistory to DatasetCreation adapter
│   │   └── ImportHistoryDetails.ts    # ImportHistory details entity
│   └── usecases/
│       ├── get-import-history-details-use-case.ts
│       └── get-recent-imports-use-case.ts
└── v1/domain/usecases/
    └── get-import-history-details-use-case.ts # New use case for detailed import data
```

### Backend File Organization
```
extralit-server/
├── src/argilla_server/api/
│   ├── handlers/v1/
│   │   └── imports.py                 # Enhanced with details endpoint
│   └── schemas/v1/
│       └── imports.py                 # Enhanced with details response
└── src/argilla_server/contexts/
    └── imports.py                     # Enhanced with details service
```

### Route Configuration
```typescript
// Enhanced ROUTES object
export const ROUTES = {
  index: "/",
  signIn: "/sign-in",
  annotationPage: (datasetId: string) => `/dataset/${datasetId}/annotation-mode`,
  settings: (id: string) => `/dataset/${id}/settings`,
  importDatasetFromHub: (id: string) => `/new/hf/${encodeURIComponent(id)}`,
  importConfiguration: (importId: string) => `/new/import/${importId}`, // New route
};
```

### Styling Integration

**Design System Consistency:**
- Reuse existing SCSS variables and mixins
- Follow established component patterns
- Maintain consistent spacing and typography
- Use existing color schemes and interaction states

**Recent Imports Sidebar Styling (based on ExampleDatasetCard):**
```scss
.recent-imports {
  display: flex;
  flex-direction: column;
  gap: $base-space;

  &__header {
    h3 {
      margin: 0 0 $base-space 0;
      font-weight: 500;
      color: var(--fg-primary);
    }

    .subtitle {
      margin: 0;
      color: var(--fg-secondary);
      font-size: 0.9rem;
    }
  }

  .imports-list {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
  }
}
```

**Import Card Styling (matching ExampleDatasetCard pattern):**
```scss
.import-card {
  &.button {
    width: 100%;
    max-width: 75%;
    padding: $base-space * 2;
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-m;
    background: var(--bg-accent-grey-2);
    color: var(--fg-primary);
    text-align: left;

    @include media("<desktop") {
      max-width: 100%;
    }

    &:hover {
      border-color: var(--bg-opacity-10);
      background: var(--bg-accent-grey-3);
    }
  }

  &__content {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
  }

  &__filename {
    margin: 0;
    color: var(--fg-primary);
    @include line-height(18px);
  }

  &__stats {
    display: flex;
    gap: $base-space;
    flex-wrap: wrap;
  }

  &__date {
    display: flex;
    align-items: center;
    gap: calc($base-space / 2);
    margin: 0;
    color: var(--fg-tertiary);
    @include font-size(12px);
  }
}
```

This design ensures seamless integration with the existing codebase while providing a robust foundation for the ImportHistory sidebar feature. The architecture leverages established patterns and components, making implementation straightforward and maintainable.