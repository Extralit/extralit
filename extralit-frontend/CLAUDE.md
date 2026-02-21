# extralit-frontend Setup

## Installation

```bash
cd extralit-frontend/

# Install dependencies
npm install
```

## Development

```bash
npm run dev              # Development server
npm run build            # Production build
```

## Running with existing server API

```bash
API_BASE_URL=https://extralit-public-demo.hf.space/ npm run dev
```

## Testing

```bash
npm run test             # Jest unit tests
npm run test:watch       # Watch mode
npm run test:coverage    # With coverage

npm run e2e              # Playwright e2e (interactive)
npm run e2e:silent       # Playwright headless
npm run e2e:report       # View test report
```

## Code Quality

```bash
npm run lint             # ESLint check
npm run lint:fix         # Fix ESLint issues
npm run format           # Format with Prettier
npm run format:check     # Check formatting
npm run generate-icons   # Generate icon components from SVG
```

## Requirements

- Node.js 18+
- Backend server running for full functionality

## Architecture

**Migration in progress**: Vuex → Pinia

- **v1/** directory: New Pinia architecture with domain-driven design
- Domain-driven design with entities, use cases, dependency injection
- Component hierarchy: base (stateless) → features (page-specific) → global (reusable)

## Key Technologies

- Vue.js + Nuxt.js
- Pinia (state management, replacing Vuex)
- Jest (unit tests) + Playwright (e2e)
- ESLint + Prettier

## Structure

```
/components      # Vue components
/v1              # New Pinia architecture
/pages           # Nuxt pages
/layouts         # Layouts
/plugins         # Plugins
/middleware      # Middleware
/assets          # Static assets
/e2e             # Playwright tests
```
