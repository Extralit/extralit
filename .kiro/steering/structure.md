# Project Structure

## Repository Organization
This is a monorepo containing multiple related packages:

```
extralit/
├── extralit-server/          # FastAPI backend server
├── extralit-frontend/        # Nuxt.js web UI
├── extralit/               # Python SDK and CLI
├── examples/               # Usage examples and deployments
└── .kiro/                  # Kiro AI assistant configuration
```

## Backend Structure (extralit-server/)
```
extralit-server/
├── src/extralit_server/
│   ├── api/                # FastAPI routes and handlers
│   │   ├── handlers/       # Request handlers by version
│   │   └── schemas/        # Pydantic models for API
│   ├── contexts/           # Business logic contexts
│   ├── models/             # SQLAlchemy database models
│   ├── jobs/               # Background job definitions
│   ├── cli/                # CLI commands
│   └── alembic/            # Database migrations
├── tests/                  # Test suite
├── docker/                 # Docker configurations
└── pyproject.toml          # PDM configuration
```

### Key Backend Patterns
- **API Handlers**: Located in `api/handlers/v1/` - one file per resource
- **Database Models**: In `models/database.py` - SQLAlchemy models
- **Business Logic**: In `contexts/` - domain-specific logic
- **Background Jobs**: In `jobs/` - RQ job definitions
- **Migrations**: Use Alembic in `alembic/versions/`

## Frontend Structure (extralit-frontend/)
```
extralit-frontend/
├── components/
│   ├── base/               # Reusable UI components
│   └── features/           # Feature-specific components
├── pages/                  # Nuxt.js pages (routes)
├── plugins/                # Vue plugins and extensions
├── assets/                 # Static assets (SCSS, icons)
├── translation/            # i18n language files
├── v1/                     # Domain and Infrastructure layers
│   ├── domain/             # Domain logic (entities, events, services, usecases)
│   │   ├── entities/
│   │   ├── events/
│   │   ├── services/
│   │   └── usecases/
│   └── infrastructure/     # Infrastructure implementations (events, repositories, services, storage, types)
│       ├── events/
│       ├── repositories/
│       ├── services/
│       ├── storage/
│       └── types/
├── e2e/                    # Playwright e2e tests
└── package.json            # npm configuration
```

### Key Frontend Patterns
- **Components**: Base components in `components/base/`, feature components in `components/features/`
- **Pages**: Nuxt.js file-based routing in `pages/`
- **Stores**: Pinia stores in `v1/store/`
- **Domain Logic**: Dependency injection in `v1/di/`
- **Axios**: @nuxt/axios makes API calls with `{proxy: true, browserBaseURL: "api"}`
- **Dependency Injection**: Use `useResolve` from `ts-injecty` for dependency resolution in use cases
- **View Models**: Use `setup(props) { return useViewModelName(props); }` pattern with the `useViewModelName.ts` file in the folder for business logic separation
- **Styling**: SCSS in `assets/scss/` with component-scoped styles
- **Base Components**: BaseSimpleTable.vue already exists for tabular data display

### Jest Testing Patterns
- **Test Files**: Place `.spec.js` files next to the component they test
- **Mock Setup**: Define mocks inline within `jest.mock()` calls to avoid hoisting issues:
  ```javascript
  // Mock dependencies inline to avoid hoisting issues
  jest.mock("ts-injecty", () => ({
    useResolve: jest.fn(() => mockUseCase),
  }));

  jest.mock("@nuxtjs/composition-api", () => ({
    ref: jest.fn(),
    computed: jest.fn(),
    watch: jest.fn(),
    onMounted: jest.fn(),
  }));
  ```
- **Mock Configuration**: Set up mocks in `beforeEach` by getting them from required modules:
  ```javascript
  beforeEach(() => {
    jest.clearAllMocks();

    const compositionApi = require("@nuxtjs/composition-api");
    mockRef = compositionApi.ref;
    mockComputed = compositionApi.computed;
    // Configure mock behavior...
  });
  ```
- **Component Stubs**: Use stubs in the mount options for base components:
  ```javascript
  wrapper = mount(ComponentName, {
    propsData: { /* props */ },
    stubs: {
      "BaseButton": {
        template: '<button class="mock-base-button"><slot /></button>',
        props: ["variant", "disabled", "loading"],
      },
      "BaseIcon": true,
      "BaseFlowModal": true,
    },
  });
  ```
- **Global Mocks**: Mock browser APIs and global functions:
  ```javascript
  beforeEach(() => {
    // Mock window.confirm for modal dialogs
    global.confirm = jest.fn(() => true);
    // Mock other browser APIs as needed
    global.alert = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });
  ```
- **View Model Testing**: Test the public interface rather than internal implementation:
  ```javascript
  // Test computed properties return expected values
  expect(computedFn()).toBe("expected-value");

  // Test methods exist and are callable
  expect(typeof viewModel.methodName).toBe("function");
  expect(viewModel.methodName).toBeDefined();

  // Test reactive state objects are returned
  expect(viewModel.property).toBe(mockRefObject);
  ```
- **Test Structure**:
  - Use `beforeEach` to reset mock state between tests
  - Use `afterEach` to clean up mocks and destroy wrappers
  - Group related tests in `describe` blocks
  - Test public interfaces, not internal implementation details
- **Props Testing**: Test component behavior with different prop combinations
- **Event Testing**: Verify component emits correct events with proper data
- **State Testing**: Test computed properties and reactive state changes
- **User Interaction**: Mock user actions and verify component responses
- **Error Handling**: Test error states and error recovery
- **Lifecycle Testing**: Test component mounting, updating, and destruction
- **Async Testing**: Use `async/await` for asynchronous operations
- **Mock Validation**: Ensure mocks match actual component interfaces

## Client SDK Structure (extralit/)
```
extralit/
├── src/
│   ├── extralit/            # Main SDK package
│   │   ├── cli/            # CLI commands
│   │   └── client/         # API client
│   └── extralit/           # Extralit-specific extensions
├── tests/                  # Test suite
├── docs/                   # Documentation
└── pyproject.toml          # PDM configuration
```

## Examples and Deployments
```
examples/
├── custom_field/           # Custom field examples
├── document_extraction/    # Document processing examples
├── deployments/
│   ├── docker/             # Docker Compose setups
│   └── k8s/                # Kubernetes manifests
└── webhooks/               # Webhook integration examples
```

## Configuration Files
- **Backend**: `extralit-server/pyproject.toml` (PDM), `.env.dev`, `.env.test`
- **Frontend**: `extralit-frontend/package.json` (npm), `nuxt.config.ts`
- **SDK**: `extralit/pyproject.toml` (PDM)
- **Docker**: `docker-compose.yaml` for local development
- **K8s**: `Tiltfile` for Kubernetes development

## Development Workflow
1. **Backend changes**: Work in `extralit-server/src/extralit_server/`
2. **Frontend changes**: Work in `extralit-frontend/components/` or `extralit-frontend/pages/`
3. **SDK changes**: Work in `extralit/src/extralit/`
4. **Tests**: Each package has its own `tests/` directory
5. **Documentation**: Use `extralit/docs/` for SDK docs

## File Naming Conventions
- **Python**: snake_case for files and modules
- **Vue/TypeScript**: PascalCase for components, camelCase for utilities
- **API endpoints**: kebab-case in URLs, snake_case in Python
- **Database**: snake_case for tables and columns
- **CSS classes**: kebab-case with BEM methodology where applicable