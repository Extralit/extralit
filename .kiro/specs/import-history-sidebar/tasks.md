# Implementation Plan

- [x] 1. Enhance backend ImportHistory API for Recent Imports
  - Add `limit` parameter support to existing `GET /api/v1/imports/history` endpoint
  - Modify query logic to support limit parameter for Recent Imports sidebar
  - Test endpoint with limit parameter to ensure proper functionality
  - _Requirements: 1.2, 1.3_

- [ ] 2. Create ImportHistory Details Use Case
  - [x] 2.1 Create GetImportHistoryDetailsUseCase class
    - Write use case class in `argilla-frontend/v1/domain/usecases/get-import-history-details-use-case.ts`
    - Implement execute method to fetch detailed ImportHistory data
    - Add proper TypeScript interfaces for ImportHistoryResponse with data field
    - _Requirements: 2.3, 3.1_

  - [x] 2.2 Enhance existing GetImportHistoryUseCase for Recent Imports
    - Add getRecent method to existing GetImportHistoryUseCase class
    - Implement method to fetch limited recent imports for sidebar
    - Reuse existing execute method with appropriate parameters
    - _Requirements: 1.2, 1.3_

- [ ] 3. Create ImportHistory Dataset Builder
  - [x] 3.1 Create ImportHistoryDatasetBuilder class
    - Write builder class in `argilla-frontend/v1/domain/entities/import/ImportHistoryDatasetBuilder.ts`
    - Implement conversion from ImportHistory data structure to DatasetCreation format
    - Add field mapping capabilities similar to HuggingFace datasets
    - Handle data type inference and validation for ImportHistory fields
    - _Requirements: 3.4, 4.1, 4.7_

  - [x] 3.2 Create ImportHistory entity types
    - Define ImportHistoryDetailsResponse interface in `argilla-frontend/v1/domain/entities/import/ImportHistoryDetails.ts`
    - Add proper TypeScript types for ImportHistory data structure
    - Ensure compatibility with existing ImportHistoryResponse from backend
    - _Requirements: 3.1, 3.3_

- [ ] 4. Create Recent Imports Sidebar Components
  - [x] 4.1 Create RecentImports component
    - Write component in `argilla-frontend/components/features/import/RecentImports.vue`
    - Implement loading, empty, and error states for recent imports
    - Add integration with GetImportHistoryUseCase for fetching recent imports
    - Include "View All Imports" and "Import Documents" buttons
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 6.1, 6.3_

  - [-] 4.2 Create RecentImportCard component
    - Write component in `argilla-frontend/components/features/import/RecentImportCard.vue`
    - Implement compact card display for individual ImportHistory records
    - Show filename, date, and summary statistics with proper styling
    - Add hover states and click interactions
    - _Requirements: 1.3, 5.3_

  - [ ] 4.3 Create RecentImports view model
    - Write view model in `argilla-frontend/components/features/import/useRecentImportsViewModel.ts`
    - Implement reactive state management for recent imports data
    - Add error handling and loading state management
    - Integrate with GetImportHistoryUseCase for data fetching
    - _Requirements: 1.5, 5.1, 5.2_

- [ ] 5. Create ImportHistory Data Preview Component
  - [ ] 5.1 Create ImportHistoryDataPreview component
    - Write component in `argilla-frontend/components/features/import/ImportHistoryDataPreview.vue`
    - Implement tabular display of ImportHistory data using BaseSimpleTable
    - Add pagination, search, and filtering capabilities for large datasets
    - Create responsive design for preview pane integration
    - _Requirements: 3.2, 3.3, 3.7_

  - [ ] 5.2 Create ImportHistoryDataPreview view model
    - Write view model for data preview component
    - Implement data transformation and filtering logic
    - Add table configuration and column management
    - Handle large dataset performance optimization
    - _Requirements: 3.2, 3.3, 5.5_

- [ ] 6. Create Import Configuration Page
  - [ ] 6.1 Create import configuration page route
    - Create page file `argilla-frontend/pages/new/import/_id.vue`
    - Implement route parameter validation and ImportHistory data fetching
    - Add loading, error, and navigation states
    - Create breadcrumb navigation with proper routing
    - _Requirements: 2.1, 2.2, 2.3, 7.1, 7.2, 7.4, 7.5_

  - [ ] 6.2 Create import configuration view model
    - Write view model for import configuration page
    - Integrate GetImportHistoryDetailsUseCase for data fetching
    - Implement error handling and retry logic
    - Add navigation and routing helper methods
    - _Requirements: 2.3, 2.4, 7.3, 7.6_

- [ ] 7. Enhance DatasetConfiguration Component for ImportHistory
  - [ ] 7.1 Modify DatasetConfiguration component props
    - Update component to accept dataSource prop ('hub' | 'import')
    - Add importData prop for ImportHistory data
    - Modify preview section to conditionally render ImportHistory or HuggingFace data
    - Ensure backward compatibility with existing HuggingFace functionality
    - _Requirements: 3.1, 3.4, 3.8, 4.1_

  - [ ] 7.2 Integrate ImportHistoryDataPreview in DatasetConfiguration
    - Replace HuggingFace iframe with ImportHistoryDataPreview when dataSource is 'import'
    - Pass ImportHistory data and field mapping to preview component
    - Maintain existing layout and styling consistency
    - _Requirements: 3.1, 3.7, 3.8_

  - [ ] 7.3 Update DatasetConfiguration view model
    - Modify useDatasetConfiguration to handle ImportHistory data
    - Integrate ImportHistoryDatasetBuilder for data conversion
    - Add support for ImportHistory field mapping and configuration
    - Ensure record.metadata.reference is populated from ImportHistory data
    - _Requirements: 3.4, 4.1, 4.2, 4.7_

- [ ] 8. Integrate Recent Imports into Home Page
  - [ ] 8.1 Modify home page sidebar
    - Update `argilla-frontend/pages/index.vue` to replace example datasets with RecentImports component
    - Add event handlers for import selection and modal opening
    - Integrate with existing workspace selection functionality
    - Maintain existing ImportModal and ImportHistoryList modal functionality
    - _Requirements: 1.1, 1.5, 2.1, 6.2, 6.4_

  - [ ] 8.2 Update home page view model
    - Modify useHomeViewModel to handle Recent Imports integration
    - Add navigation methods for import configuration routing
    - Integrate modal opening logic for ImportHistoryList and ImportModal
    - _Requirements: 2.1, 6.2, 6.4, 6.5_

- [ ] 9. Add Import Configuration Route
  - [ ] 9.1 Update routes configuration
    - Add importConfiguration route to ROUTES object in `argilla-frontend/v1/infrastructure/services/useRoutes.ts`
    - Implement goToImportConfiguration navigation method
    - Ensure proper route parameter handling for import_id
    - _Requirements: 2.1, 2.2, 7.1_

  - [ ] 9.2 Update routing integration
    - Integrate new route with existing navigation patterns
    - Add proper breadcrumb support for import configuration
    - Ensure browser back/forward navigation works correctly
    - _Requirements: 7.4, 7.5_

- [ ] 10. Add Styling and Responsive Design
  - [ ] 10.1 Style Recent Imports components
    - Create SCSS styles for RecentImports and RecentImportCard components
    - Follow existing design system patterns and variables from ExampleDatasetCard styling
    - Implement responsive design for sidebar display
    - Add hover states and interaction feedback matching ExampleDatasetCard
    - _Requirements: 5.3, 5.4_

  - [ ] 10.2 Style ImportHistory Data Preview
    - Create SCSS styles for ImportHistoryDataPreview component
    - Ensure consistent styling with existing table components
    - Implement responsive design for preview pane
    - Add loading and empty state styling
    - _Requirements: 3.2, 5.4_

  - [ ] 10.3 Update Import Configuration page styling
    - Style import configuration page layout and components
    - Ensure consistent breadcrumb and navigation styling
    - Add responsive design for mobile devices
    - Maintain consistency with existing dataset configuration styling
    - _Requirements: 5.4, 7.4_

- [ ] 11. Testing and Error Handling
  - [ ] 11.1 Add error handling for ImportHistory operations
    - Implement proper error handling in all ImportHistory use cases
    - Add retry mechanisms for failed API requests
    - Create user-friendly error messages and recovery options
    - Handle edge cases like missing or corrupted ImportHistory data
    - _Requirements: 2.5, 5.1, 5.6_

  - [ ] 11.2 Add loading states and performance optimization
    - Implement loading indicators for all async operations
    - Add skeleton screens for better user experience
    - Optimize performance for large ImportHistory datasets
    - Implement proper cleanup for component unmounting
    - _Requirements: 1.6, 3.5, 5.1, 5.2, 5.5_

- [ ] 12. Integration Testing and Validation
  - [ ] 12.1 Test Recent Imports sidebar functionality
    - Verify Recent Imports display and interaction
    - Test workspace selection integration
    - Validate modal opening and navigation
    - Test responsive design on different screen sizes
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 5.4, 6.1, 6.3_

  - [ ] 12.2 Test Import Configuration workflow
    - Verify end-to-end navigation from Recent Imports to configuration
    - Test ImportHistory data loading and display
    - Validate DatasetConfiguration integration with ImportHistory data
    - Test dataset creation from ImportHistory data
    - _Requirements: 2.1, 2.3, 3.1, 3.4, 4.1, 4.2, 4.7_

  - [ ] 12.3 Test error scenarios and edge cases
    - Test invalid import_id handling and error messages
    - Verify proper error handling for missing or corrupted data
    - Test network failure scenarios and retry mechanisms
    - Validate proper cleanup and memory management
    - _Requirements: 2.5, 7.2, 7.6_