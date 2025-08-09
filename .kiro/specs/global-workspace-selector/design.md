# Design Document

## Overview

The Global Workspace Selector feature implements a centralized workspace management system that moves workspace selection from local component filters to a persistent, header-based selector. The design leverages existing Pinia store patterns, local storage services, and component architecture to create a seamless workspace context that persists across all application pages.

The solution integrates workspace selection into the BaseBreadcrumbs component within the AppHeader, providing immediate access to workspace switching while maintaining consistency with existing UI patterns. The design emphasizes reusability of existing components and follows established architectural patterns for state management and persistence.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Application"
        AppHeader[AppHeader Component]
        BaseBreadcrumbs[BaseBreadcrumbs Component]
        WorkspaceSelector[WorkspaceSelector Component]

        subgraph "State Management"
            WorkspaceStore[Workspace Pinia Store with Persistence]
        end

        subgraph "Domain Layer"
            WorkspaceEntity[Workspace Entity]
            IWorkspaceStorage[IWorkspaceStorage Interface]
            GetWorkspacesUseCase[GetWorkspaces UseCase]
        end

        subgraph "Infrastructure Layer"
            WorkspaceRepository[Workspace Repository]
            WorkspaceStorage[Workspace Storage Implementation]
        end

        subgraph "Page Components"
            HomePage[Home Page]
            DatasetList[Dataset List]
            DocumentsList[Documents List]
        end
    end

    subgraph "Backend API"
        WorkspaceAPI["/v1/me/workspaces"]
    end

    AppHeader --> BaseBreadcrumbs
    BaseBreadcrumbs --> WorkspaceSelector
    WorkspaceSelector --> WorkspaceStore
    WorkspaceStore --> GetWorkspacesUseCase
    GetWorkspacesUseCase --> WorkspaceRepository
    WorkspaceRepository --> WorkspaceAPI
    WorkspaceStore --> HomePage
    HomePage --> DatasetList
    HomePage --> DocumentsList
```

### Component Integration Flow

```mermaid
sequenceDiagram
    participant User
    participant AppHeader
    participant BaseBreadcrumbs
    participant WorkspaceSelector
    participant WorkspaceStore
    participant API

    User->>AppHeader: Load page
    AppHeader->>BaseBreadcrumbs: Render breadcrumbs
    BaseBreadcrumbs->>WorkspaceSelector: Include workspace selector
    WorkspaceSelector->>WorkspaceStore: Get workspace state
    WorkspaceStore->>WorkspaceStore: Restore from localStorage
    WorkspaceStore->>API: Fetch workspace list
    API-->>WorkspaceStore: Return workspaces
    WorkspaceStore-->>WorkspaceSelector: Provide workspace data
    WorkspaceSelector-->>BaseBreadcrumbs: Render workspace dropdown

    User->>WorkspaceSelector: Select different workspace
    WorkspaceSelector->>WorkspaceStore: Update selected workspace
    WorkspaceStore->>WorkspaceStore: Persist to localStorage
    WorkspaceStore-->>DatasetList: Notify workspace change
    WorkspaceStore-->>DocumentsList: Notify workspace change
```

## Components and Interfaces

### Core Components

#### 1. Enhanced BaseBreadcrumbs Component

**Purpose**: Integrate workspace selector into breadcrumb navigation
**Location**: `components/base/base-breadcrumbs/BaseBreadcrumbs.vue`

**Key Features**:
- Embed WorkspaceSelector component before breadcrumb items
- Maintain existing breadcrumb functionality
- Responsive layout adaptation for workspace selector
- Event handling for workspace selection

**Props**:
```typescript
interface BaseBreadcrumbsProps {
  breadcrumbs: BreadcrumbItem[]
  copyButton?: boolean
  showWorkspaceSelector?: boolean // New prop
}
```

#### 2. Workspace Selector Integration

**Purpose**: Reuse existing WorkspaceSelector component in header context
**Location**: Reuse `components/features/home/dataset-list/workspaces-filter/WorkspaceSelector.vue`

**Adaptations**:
- Style adjustments for header layout
- Integration with global workspace store
- Event emission for workspace changes

#### 3. Enhanced AppHeader Component

**Purpose**: Coordinate workspace selector integration
**Location**: `components/features/global/AppHeader.vue`

**Key Features**:
- Pass workspace selector visibility flag to BaseBreadcrumbs
- Handle workspace change events
- Maintain existing header functionality

### State Management Layer

#### 1. Workspace Storage Interface

**Purpose**: Define contract for workspace state management
**Location**: `v1/domain/services/IWorkspaceStorage.ts`

```typescript
export interface IWorkspaceStorage {
  saveWorkspaces(workspaces: Workspace[]): void
  saveSelectedWorkspace(workspace: Workspace | null): void
}
```

#### 2. Workspace Storage Implementation

**Purpose**: Pinia store implementation for workspace state with integrated persistence
**Location**: `v1/infrastructure/storage/WorkspaceStorage.ts`

**Key Features**:
- Workspace list management
- Selected workspace persistence via localStorage
- Reactive state updates
- Integrated persistence following existing DatasetsStorage pattern

```typescript
class WorkspaceState {
  constructor(
    public readonly workspaces: Workspace[] = [],
    public readonly selectedWorkspace: Workspace | null = null
  ) {}
}

export const useWorkspaces = () => {
  const workspaceStore = useStoreForWorkspaces();

  const saveWorkspaces = (workspaces: Workspace[]) => {
    workspaceStore.save(new WorkspaceState(workspaces, workspaceStore.get().selectedWorkspace));
  };

  const saveSelectedWorkspace = (workspace: Workspace | null) => {
    workspaceStore.save(new WorkspaceState(workspaceStore.get().workspaces, workspace));
  };

  return { ...workspaceStore, saveWorkspaces, saveSelectedWorkspace };
};
```

### Domain Layer

#### 1. Enhanced Workspace Entity

**Purpose**: Extend existing Workspace entity if needed
**Location**: `v1/domain/entities/workspace/Workspace.ts`

**Current Structure**:
```typescript
export class Workspace {
  constructor(
    public readonly id: string,
    public readonly name: string
  ) {}
}
```

#### 2. Get Workspaces Use Case

**Purpose**: Orchestrate workspace fetching and state management
**Location**: `v1/domain/usecases/get-workspaces-use-case.ts`

**Key Features**:
- Fetch workspaces from repository
- Update workspace store
- Handle error scenarios
- Restore selected workspace from persistence

## Data Models

### Workspace State Model

```typescript
interface WorkspaceState {
  workspaces: Workspace[]
  selectedWorkspace: Workspace | null
  isLoading: boolean
  error: string | null
}
```

### Workspace Selection Event

```typescript
interface WorkspaceSelectionEvent {
  workspace: Workspace | null
  previousWorkspace: Workspace | null
  source: 'user-selection' | 'auto-selection' | 'persistence-restore'
}
```

### Local Storage Schema

```typescript
interface WorkspaceStorageSchema {
  selectedWorkspaceId: string | null
  workspacePreferences: {
    [workspaceId: string]: {
      lastAccessed: string
      preferences: Record<string, any>
    }
  }
}
```

## Error Handling

### Error Scenarios and Responses

1. **Workspace API Failure**
   - Display error message in workspace selector
   - Provide retry mechanism
   - Fall back to cached workspace data if available

2. **Invalid Persisted Workspace**
   - Automatically select first available workspace
   - Clear invalid workspace from local storage
   - Log warning for debugging

3. **Local Storage Unavailable**
   - Continue with session-only workspace selection
   - Display warning about lack of persistence
   - Gracefully degrade functionality

4. **Workspace Access Revoked**
   - Remove workspace from available list
   - Auto-select alternative workspace
   - Notify user of access change

### Error Recovery Strategies

```typescript
interface ErrorRecoveryStrategy {
  retryAttempts: number
  fallbackWorkspace: Workspace | null
  userNotification: boolean
  logLevel: 'info' | 'warn' | 'error'
}
```

## Testing Strategy

### Unit Testing

1. **Workspace Storage Tests**
   - Test Pinia store state management
   - Verify local storage integration
   - Test reactive updates

2. **Component Integration Tests**
   - Test BaseBreadcrumbs with workspace selector
   - Verify workspace selection events
   - Test responsive layout behavior

3. **Use Case Tests**
   - Test workspace fetching logic
   - Verify error handling scenarios
   - Test persistence restoration

### Integration Testing

1. **End-to-End Workspace Flow**
   - Test complete workspace selection workflow
   - Verify persistence across page navigation
   - Test workspace filtering in dataset/document lists

2. **Error Scenario Testing**
   - Test API failure handling
   - Verify graceful degradation
   - Test recovery mechanisms

### Component Testing

1. **WorkspaceSelector Component**
   - Test dropdown functionality
   - Verify search filtering
   - Test selection events

2. **BaseBreadcrumbs Enhancement**
   - Test workspace selector integration
   - Verify existing breadcrumb functionality
   - Test responsive behavior

## Implementation Phases

### Phase 1: Core Infrastructure
- Create workspace storage interface and implementation
- Implement workspace persistence service
- Create enhanced get workspaces use case

### Phase 2: Component Integration
- Enhance BaseBreadcrumbs component
- Integrate WorkspaceSelector into header
- Update AppHeader component

### Phase 3: State Management
- Implement global workspace store
- Add reactive workspace filtering
- Update existing components to use global state

### Phase 4: Testing and Polish
- Implement comprehensive test suite
- Add error handling and recovery
- Performance optimization and accessibility

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**
   - Load workspace data only when needed
   - Cache workspace list with appropriate TTL

2. **Reactive Updates**
   - Use computed properties for filtered data
   - Minimize unnecessary re-renders

3. **Local Storage Efficiency**
   - Store only essential workspace data
   - Implement storage cleanup for old preferences

4. **API Optimization**
   - Leverage existing caching mechanisms
   - Batch workspace-related API calls

### Memory Management

- Proper cleanup of event listeners
- Efficient Pinia store state management
- Avoid memory leaks in component lifecycle