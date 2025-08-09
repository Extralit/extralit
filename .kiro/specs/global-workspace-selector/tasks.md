# Implementation Plan

- [x] 1. Create workspace storage infrastructure
  - Create IWorkspaceStorage interface following existing storage patterns
  - Implement WorkspaceStorage Pinia store with integrated localStorage persistence
  - _Requirements: 2.1, 2.2, 6.1, 6.2_

- [x] 1.1 Create workspace storage interface
  - Write IWorkspaceStorage interface in `v1/domain/services/IWorkspaceStorage.ts`
  - Define methods for saving workspaces, selected workspace, and getting selected workspace
  - Follow existing interface patterns from IDatasetsStorage
  - _Requirements: 2.4, 7.1_

- [x] 1.2 Implement workspace Pinia store with integrated persistence
  - Create WorkspaceStorage.ts in `v1/infrastructure/storage/` following DatasetsStorage pattern
  - Implement WorkspaceState class with workspaces array and selectedWorkspace properties
  - Create useWorkspaces composable with saveWorkspaces and saveSelectedWorkspace methods
  - Integrate localStorage persistence directly in the store following existing patterns
  - Use existing useStoreFor pattern from create.ts
  - _Requirements: 2.1, 2.2, 2.6, 6.1, 6.2, 6.4, 6.5_

- [x] 2. Enhance workspace use case and repository integration
  - Update GetWorkspacesUseCase to work with new workspace storage
  - Integrate workspace persistence with workspace fetching
  - Add error handling for workspace API failures
  - _Requirements: 2.5, 8.1, 8.2_

- [x] 2.1 Update GetWorkspacesUseCase
  - Modify existing GetWorkspacesUseCase to use new workspace storage
  - Add logic to restore selected workspace from localStorage after fetching
  - Implement auto-selection of first workspace when none is selected
  - Add error handling and retry mechanisms
  - _Requirements: 1.5, 2.5, 8.1, 8.4_

- [x] 2.2 Add workspace repository error handling
  - Enhance existing WorkspaceRepository error handling if needed
  - Ensure proper error propagation to use cases
  - Add retry logic for failed workspace API calls
  - _Requirements: 8.1, 8.6_

- [x] 3. Create workspace breadcrumb dropdown component
  - Create WorkspaceBreadcrumbDropdown component for breadcrumb integration
  - Integrate with global workspace store
  - Add proper styling for breadcrumb context
  - _Requirements: 3.1, 3.2, 5.1, 5.2_

- [x] 3.1 Create WorkspaceBreadcrumbDropdown component
  - Create new component in `components/base/base-breadcrumbs/WorkspaceBreadcrumbDropdown.vue`
  - Reuse existing WorkspaceSelector logic with breadcrumb-specific styling
  - Connect to global workspace store using useWorkspaces composable
  - Handle workspace selection events and emit breadcrumb link updates
  - _Requirements: 3.2, 3.5, 5.4_

- [x] 3.2 Style workspace dropdown for breadcrumb context
  - Style dropdown to match breadcrumb item appearance
  - Ensure dropdown positioning works correctly in breadcrumb context
  - Add hover states and active workspace indication
  - Maintain existing breadcrumb visual hierarchy
  - _Requirements: 3.6, 5.3, 5.7_

- [x] 4. Enhance BaseBreadcrumbs component for workspace detection
  - Add workspace breadcrumb detection and rendering logic
  - Implement conditional rendering for workspace breadcrumb items
  - Maintain existing breadcrumb functionality for non-workspace items
  - _Requirements: 3.1, 3.3, 5.1_

- [x] 4.1 Add workspace breadcrumb detection to BaseBreadcrumbs
  - Modify BaseBreadcrumbs.vue to detect workspace breadcrumb items (isWorkspace flag)
  - Render WorkspaceBreadcrumbDropdown for workspace items
  - Render normal breadcrumb items for non-workspace items
  - Handle workspace selection events and link updates
  - _Requirements: 3.1, 3.3_

- [x] 4.2 Update breadcrumb item structure
  - Extend BreadcrumbItem interface to include isWorkspace and workspaceId properties
  - Update breadcrumb rendering logic to handle workspace-specific properties
  - Ensure backward compatibility with existing breadcrumb usage
  - Add TypeScript types for enhanced breadcrumb structure
  - _Requirements: 3.6, 5.7_

- [x] 5. Update breadcrumb generation in view models
  - Modify view models to generate workspace-aware breadcrumbs
  - Add isWorkspace flags to workspace breadcrumb items
  - Ensure dynamic link generation for workspace changes
  - _Requirements: 3.1, 3.4_

- [x] 5.1 Update useDatasetViewModel breadcrumb generation
  - Modify createRootBreadCrumbs in useDatasetViewModel.ts to mark workspace breadcrumbs
  - Add isWorkspace: true flag to workspace breadcrumb items
  - Include workspaceId in workspace breadcrumb items
  - Ensure workspace breadcrumb links update dynamically
  - _Requirements: 3.1, 3.4_

- [x] 6. Update home page breadcrumbs and workspace integration
  - Update home page to use workspace-aware breadcrumbs
  - Remove workspace filter from DatasetList component
  - Ensure dataset and document filtering works with global workspace
  - _Requirements: 4.1, 4.2, 4.3, 5.5_

- [x] 6.1 Update home page breadcrumb generation
  - Modify useHomeViewModel.ts to generate workspace-aware breadcrumbs
  - Add computed breadcrumbs property that includes workspace breadcrumb when workspace is selected
  - Update index.vue to use dynamic breadcrumbs from useHomeViewModel
  - Add isWorkspace flag to workspace breadcrumb items on home page
  - Ensure home breadcrumb shows current workspace context
  - Remove workspace filter from DatasetList component
  - _Requirements: 4.1, 5.5_

- [x] 6.2 Add dynamic breadcrumb generation to useHomeViewModel
  - Add computed breadcrumbs property to useHomeViewModel.ts
  - Generate breadcrumbs based on selected workspace state: `[{ name: 'Home' }]` or `[{ name: 'Home' }, { name: workspace.name, isWorkspace: true, workspaceId: workspace.id }]`
  - Connect breadcrumbs to global workspace store
  - Update breadcrumb links to include workspace parameter when workspace is selected
  - _Requirements: 4.2, 4.3, 2.3_

- [x] 6.3 Update useHomeViewModel for global workspace state
  - Modify useHomeViewModel.ts to use global workspace store instead of local workspace state
  - Remove local workspace state management (workspaces, selectedWorkspace refs)
  - Connect dataset and document filtering to global workspace selection
  - Update workspace change handlers to use global state
  - _Requirements: 4.2, 4.3, 2.3_

- [x] 6.4 Update home page template to use dynamic breadcrumbs
  - Modify index.vue to use breadcrumbs from useHomeViewModel instead of static breadcrumbs
  - Remove hardcoded breadcrumbs array from AppHeader component
  - Ensure breadcrumb actions are properly handled for workspace changes
  - _Requirements: 4.2, 4.3_

- [x] 6.5 Update DocumentsList component integration
  - Ensure DocumentsList component receives workspace from global state
  - Remove workspace prop passing from home page template
  - Update DocumentsList to reactively respond to workspace changes
  - _Requirements: 4.2, 4.3_

- [ ] 7. Implement workspace URL parameter integration
  - Add workspace ID to URL parameters when workspace is selected
  - Restore workspace selection from URL parameters on page load
  - Update routing to maintain workspace context
  - _Requirements: 4.5, 4.6_

- [ ] 7.1 Add workspace URL parameter handling
  - Update useHomeViewModel to read workspace from URL query parameters
  - Add logic to set workspace selection based on URL parameter
  - Implement URL parameter updates when workspace selection changes
  - Ensure URL parameters work with browser back/forward navigation
  - _Requirements: 4.5, 4.6_

- [ ] 8. Add workspace change event handling
  - Implement reactive updates for workspace-dependent components
  - Add cache invalidation for workspace-dependent API calls
  - Ensure all components respond to workspace changes
  - _Requirements: 2.3, 2.7, 4.4_

- [ ] 8.1 Implement workspace change reactivity
  - Add watchers in components that depend on workspace selection
  - Implement automatic data refresh when workspace changes
  - Add cache invalidation for workspace-dependent API endpoints
  - Ensure smooth transitions between workspace selections
  - _Requirements: 2.3, 2.7, 4.4_

- [ ] 9. Add comprehensive error handling
  - Implement error handling for workspace API failures
  - Add graceful fallbacks for invalid workspace selections
  - Create user-friendly error messages and recovery options
  - _Requirements: 8.1, 8.2, 8.3, 8.7_

- [ ] 9.1 Implement workspace error handling
  - Add error states to workspace store for API failures
  - Implement retry mechanisms for failed workspace requests
  - Add user notifications for workspace access changes
  - Create fallback logic for when no workspaces are available
  - _Requirements: 8.1, 8.2, 8.3, 8.7_

- [ ] 9.2 Add workspace validation and recovery
  - Implement validation for persisted workspace selections
  - Add automatic fallback to first available workspace for invalid selections
  - Create recovery mechanisms for workspace access revocation
  - Add logging for workspace-related errors and state changes
  - _Requirements: 8.2, 8.4, 8.7_

- [ ] 10. Create comprehensive test suite
  - Write unit tests for workspace storage and persistence
  - Create component tests for workspace selector integration
  - Add integration tests for workspace filtering functionality
  - _Requirements: All requirements validation_

- [ ] 10.1 Write workspace storage unit tests
  - Test WorkspaceStorage Pinia store functionality
  - Test workspace persistence service with local storage
  - Test workspace use case with error scenarios
  - Mock dependencies and test reactive state updates
  - _Requirements: 2.1, 2.2, 6.1, 6.2_

- [ ] 10.2 Create workspace selector component tests
  - Test WorkspaceHeaderSelector component integration
  - Test BaseBreadcrumbs with workspace selector enabled
  - Test workspace selection events and state updates
  - Test responsive behavior and styling
  - _Requirements: 3.1, 3.2, 3.5, 3.6_

- [ ] 10.3 Add integration tests for workspace filtering
  - Test end-to-end workspace selection workflow
  - Test dataset and document filtering with workspace changes
  - Test URL parameter integration and persistence
  - Test error handling and recovery scenarios
  - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6_