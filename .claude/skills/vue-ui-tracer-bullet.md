---
description: Build or edit a Vue.js 2 + Nuxt UI component end-to-end using the Tracer Bullet approach — fire one thin wire through the full stack first, confirm it works, then expand.
---

## Tracer Bullet Steps

Work in this order. Do not build stubs; wire one real path per step and verify it renders/passes before expanding.

1. **Read the adjacent component** most similar to what you're building to internalize current patterns before writing a line.
2. **Create the ViewModel** (`useXxxViewModel.ts`) with one reactive ref and one method — enough to confirm DI and reactivity work.
3. **Create the component** (`Xxx.vue`) with the minimal template that proves the ViewModel connection: one binding, one event.
4. **Wire into parent** — add the `<Xxx>` tag and required props; confirm it mounts and the basic path renders.
5. **Expand** — add remaining computed/watch/methods in the ViewModel, then fill the template.
6. **Add types** in `types.ts` once the shape stabilises.
7. **Write spec** (`Xxx.spec.js`) last, covering the ViewModel logic.

---

## File Anatomy

```
components/features/<domain>/
├── Xxx.vue                    # Thin template + Options API shell
├── useXxxViewModel.ts         # Fat Composition API hook (all logic here)
├── types.ts                   # Shared TS interfaces for this feature
└── Xxx.spec.js                # Jest tests (ViewModel-focused)
```

### `Xxx.vue` — what goes where

| Section | Content |
|---|---|
| `props` | Typed inputs; always provide `default` |
| `emits` | Declare every emitted event |
| `data()` | **Local UI state only** (e.g. `localToggle`, row edits not owned by ViewModel) |
| `computed` | Derives from both `data()` and ViewModel refs via `this.` |
| `watch` | Observe ViewModel refs or computed; call `this.emitUpdate()` etc. |
| `methods` | Event handlers, formatters, local mutations |
| `setup(props)` | **Only line**: `return useXxxViewModel(props)` |

### `useXxxViewModel.ts` — structure

```typescript
import { ref, computed, watch } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import { SomethingUseCase } from "~/v1/domain/usecases/something-use-case";

export const useXxxViewModel = (props: { workspace: Workspace | null }) => {
  const someUseCase = useResolve(SomethingUseCase);  // DI
  const isLoading = ref(false);
  const data = ref<Something | null>(null);

  const load = async () => { /* ... */ };

  watch(() => props.workspace?.id, (id) => { if (id) load(); }, { immediate: true });

  return { isLoading, data, load };
};
```

---

## Critical Pitfall: ts-plugin + Options API + `setup()`

**Problem**: When a component has both `methods: {}` AND `setup()`, the Vue language plugin types the template `this` as `Vue3Instance<DataType>` — which only sees `data()` fields and `setup()` returns. Methods from the `methods:{}` block are **invisible to the template type checker**, causing:

```
Property 'handleFoo' does not exist on type 'Vue3Instance<...>'
```

**This is an IDE-only error** (ts-plugin, not tsc). It does not affect runtime or `npm run build`.

**Workarounds** (pick one per handler):

```vue
<!-- Option A: inline arrow (preferred for custom component events) -->
@cell-edited="(cell) => handleCellEdit(cell)"

<!-- Option B: move the handler into setup()'s return -->
setup(props) {
  const vm = useXxxViewModel(props);
  const handleFoo = () => { /* can't use `this` */ };
  return { ...vm, handleFoo };
}
```

**Rule of thumb**: If the ts-plugin error is on a custom component event (`@cell-edited`, `@table-built`), use Option A. If it's on a standard DOM event (`@click`), it usually resolves itself.

**Inside computed properties that return config objects** (e.g. Tabulator column configs with callbacks), capture `this` early:

```typescript
editableTableColumns() {
  const vm = this as any;  // capture before entering non-Vue callbacks
  return [{
    editorParams(cell: any) {
      const rows = vm.editableTableData;  // safe closure
    }
  }];
}
```

---

## DDD Quick Reference

```
v1/
├── domain/
│   ├── entities/          # Data shapes — import here everywhere
│   ├── usecases/          # Business logic — one class per operation
│   └── services/          # Interfaces (ports) for repos/services
├── infrastructure/
│   ├── repositories/      # HTTP implementations of service interfaces
│   └── storage/           # Pinia stores
└── di/di.ts               # register() all use cases here
```

**Adding a new use case:**
1. Create `v1/domain/usecases/do-thing-use-case.ts` (class with `constructor(private axios)`)
2. Register in `v1/di/di.ts`: `register(DoThingUseCase).withDependency(useAxios).build()`
3. Inject in ViewModel: `const doThing = useResolve(DoThingUseCase)`

---

## SCSS Cheatsheet

```scss
// Spacing — always multiples of $base-space (8px)
gap: $base-space * 2;          // 16px
padding: $base-space * 3;      // 24px

// Color tokens — never hardcode colors
color: var(--fg-primary);
background: var(--bg-accent-grey-1);
border: 1px solid var(--border-field);
// States: --color-success, --color-danger, --color-warning, --bg-action

// Border radius
border-radius: $border-radius;    // 5px (default)
border-radius: $border-radius-m;  // 10px (cards/panels)

// Pierce child component styles
:deep(.tabulator) { ... }

// Scoped BEM-ish
.my-component {
  &__header { ... }
  &__body { ... }
  &--loading { opacity: 0.6; }
}
```

---

## Test Pattern

```javascript
// useXxxViewModel.spec.js
import { useXxxViewModel } from "./useXxxViewModel";

jest.mock("ts-injecty", () => ({ useResolve: jest.fn() }));
jest.mock("~/v1/domain/usecases/something-use-case");

describe("useXxxViewModel", () => {
  let emit;
  beforeEach(() => { emit = jest.fn(); });

  it("initializes with empty state", () => {
    const vm = useXxxViewModel({ workspace: null }, { emit });
    expect(vm.data.value).toBeNull();
  });

  it("loads data when workspace provided", async () => {
    const vm = useXxxViewModel({ workspace: { id: "ws1" } }, { emit });
    await vm.load();
    expect(vm.isLoading.value).toBe(false);
  });
});
```

**Testing components**: mount shallowly, stub child components, assert emitted events. See `ImportAnalysisTable.spec.js` for a full example.
