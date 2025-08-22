# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Extralit frontend codebase.

## Frontend Architecture Overview

Extralit frontend is a Vue.js/Nuxt.js web application for scientific literature data extraction and annotation with human-in-the-loop workflows.

**Tech Stack:**
- **Vue 2.7 + Nuxt 2** with Composition API support via `@nuxtjs/composition-api`
- **TypeScript** for type safety
- **SCSS** with design system and component-scoped styles
- **Pinia** for state management (transitioning from Vuex)
- **Domain-Driven Design** with clean architecture principles

## Development Commands

```bash
# Development
npm run dev              # Start development server with hot reload
npm run build            # Production build
npm run start            # Start production server (after build)

# Testing
npm run test             # Run Jest unit tests
npm run test:watch       # Run tests in watch mode
npm run test:coverage    # Run tests with coverage report
npm run e2e              # Run Playwright e2e tests (interactive UI)
npm run e2e:silent       # Run e2e tests in headless mode
npm run e2e:report       # Show Playwright test report

# Code Quality
npm run lint             # ESLint check
npm run lint:fix         # Fix ESLint issues automatically
npm run format           # Format code with Prettier
npm run format:check     # Check formatting without modifying files

# Assets
npm run generate-icons   # Generate icon components from SVG files
```

## Architecture Patterns

### Domain-Driven Design Structure

The `v1/` directory contains the new clean architecture implementation:

```
v1/
├── domain/                    # Business logic layer
│   ├── entities/              # Domain entities and types
│   ├── events/                # Domain events (Event suffix)
│   ├── services/              # Domain service interfaces (I prefix)
│   └── usecases/              # Use case implementations (kebab-case, use-case suffix)
├── infrastructure/            # Technical implementation layer
│   ├── events/                # Event handlers (EventHandler suffix)
│   ├── repositories/          # API repository implementations (Repository suffix)
│   ├── services/              # UI hooks and utilities (use* pattern)
│   ├── storage/               # Client-side storage (Storage suffix)
│   └── types/                 # Infrastructure types and API models
├── di/                        # Dependency injection container
└── store/                     # Pinia stores
```

### Component Architecture

```
components/
├── base/                      # Stateless, reusable UI components
│   ├── base-button/           # BaseButton.vue
│   ├── base-input/            # BaseInput.vue
│   └── base-modal/            # BaseModal.vue, etc.
├── features/                  # Feature-specific components by domain
│   ├── annotation/            # Annotation workflow components
│   ├── dataset-creation/      # Dataset creation components
│   ├── documents/             # Document management components
│   └── user-settings/         # User settings components
└── components/                # Legacy component organization (being phased out)
```

### View Model Pattern

Components use the view model pattern for separation of concerns:

```typescript
// Component setup
export default {
  setup(props) {
    return useComponentNameViewModel(props);
  }
};

// View model composable
export function useComponentNameViewModel(props) {
  // Business logic, API calls, reactive state
  return {
    // Reactive properties and methods for template
  };
}
```

### Dependency Injection

Services are registered in `v1/di/di.ts` using the `ts-injecty` container:

```typescript
// Registration
register(UseCase).withDependency(Repository).build()

// Usage in composables
const useCase = useResolve(UseCase);
```

## Key Development Patterns

### API Communication

- **Repositories**: Handle API communication (`v1/infrastructure/repositories/`)
- **Axios Integration**: Uses `@nuxtjs/axios` with proxy configuration
- **Base URL**: All API calls go through `/api/` proxy to backend
- **Error Handling**: Centralized in `plugins/axios/axios-global-handler.ts`

### State Management

- **Pinia Stores**: New state management in `v1/store/`
- **Storage Services**: Client-side persistence in `v1/infrastructure/storage/`
- **Reactive State**: Using Composition API reactivity

### Component Patterns

- **Base Components**: Stateless, prop-driven components in `components/base/`
- **Feature Components**: Domain-specific components with business logic
- **View Models**: Business logic extracted to composable functions
- **Props & Events**: TypeScript interfaces for component contracts

### Testing Patterns

#### Unit Tests (Jest)

```typescript
// Component testing
import { mount } from '@vue/test-utils';
import Component from './Component.vue';

describe('Component', () => {
  it('should render correctly', () => {
    const wrapper = mount(Component);
    expect(wrapper.exists()).toBe(true);
  });
});
```

Configuration in `jest.config.js`:
- Uses `@vue/vue2-jest` for Vue SFC transformation
- Module aliases for `~` and `@` paths
- JSDOM environment for DOM testing
- Coverage collection from components and pages

#### E2E Tests (Playwright)

```typescript
// Page object model
import { test, expect } from '@playwright/test';

test('annotation workflow', async ({ page }) => {
  await page.goto('/dataset/123');
  await expect(page.locator('[data-testid="record-form"]')).toBeVisible();
});
```

Configuration in `playwright.config.ts`:
- Screenshot comparison for visual regression testing
- API mocking in `e2e/common/` directory
- Page object patterns for reusable test utilities

### Styling Patterns

- **SCSS Architecture**: Organized in `assets/scss/` with abstracts, base, and components
- **Component Scoped**: Use `<style scoped>` for component-specific styles
- **Design System**: Consistent spacing, colors, and typography via SCSS variables
- **Responsive**: Mobile-first approach with mixins in `assets/scss/abstract/mixins/`

### Internationalization

- **i18n**: 4 languages supported (en, de, es, ja) in `translation/` directory
- **Strategy**: No prefix strategy for cleaner URLs
- **Fallback**: English as default fallback language

## Common Development Tasks

### Adding New Components

1. Create component in appropriate `components/` subdirectory
2. Follow naming convention: `ComponentName.vue`
3. Add TypeScript props interface
4. Create view model composable if business logic is needed
5. Add unit tests in same directory

### Creating Use Cases

1. Define interface in `v1/domain/services/`
2. Implement use case in `v1/domain/usecases/`
3. Create repository if API access needed
4. Register dependencies in `v1/di/di.ts`
5. Add unit tests for business logic

### API Integration

1. Define API types in `v1/infrastructure/types/`
2. Create repository in `v1/infrastructure/repositories/`
3. Implement use case consuming repository
4. Register dependencies in DI container
5. Use in view models via `useResolve()`

### Running Tests

- **Unit Tests**: Focus on business logic and component behavior
- **E2E Tests**: Critical user workflows and integration scenarios
- **Coverage**: Aim for high coverage on use cases and view models
- **CI**: Tests run automatically in GitHub Actions

### File Organization

- **Kebab-case**: For directory names (`user-settings/`)
- **PascalCase**: For component files (`UserSettings.vue`)
- **camelCase**: For variables and functions
- **Interfaces**: Prefix with `I` for service interfaces

### Performance Considerations

- **Code Splitting**: Nuxt handles automatic code splitting
- **Lazy Loading**: Use dynamic imports for heavy components
- **Bundle Analysis**: Use `npm run build` with analyze option
- **Image Optimization**: Use appropriate formats and sizes