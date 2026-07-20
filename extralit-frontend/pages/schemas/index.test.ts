import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, shallowMount } from "@vue/test-utils";
import { ref } from "vue";
import { createPinia, setActivePinia } from "pinia";
import Container from "ts-injecty";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import * as useEnsureWorkspacesModule from "~/composables/useEnsureWorkspaces";
import SchemasPage from "./index.vue";

// The page hydrates workspaces via useEnsureWorkspaces (which resolves GetWorkspacesUseCase
// from DI). Mock the composable so tests don't need the workspace use-case registered.
vi.mock("~/composables/useEnsureWorkspaces", () => ({
  useEnsureWorkspaces: vi.fn(() => ({ ensureWorkspaces: vi.fn(async () => {}), selectedWorkspace: ref(null) })),
}));

const SCHEMA = new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "2026-01-01", "2026-01-01");

// InternalPage is a layout wrapper; render its header + page-content slots so the page body
// is visible under shallowMount. Named stubs keep findComponent({ name }) working.
const stubs = {
  InternalPage: { template: "<div><slot name='header' /><slot name='page-content' /></div>" },
  AppHeader: { name: "AppHeader", template: "<div class='app-header' />" },
  BaseLoading: true,
  NuxtLink: { template: "<a><slot /></a>" },
  V2StatusBadge: { name: "V2StatusBadge", template: "<span>{{ status }}</span>", props: ["status"] },
  V2Empty: { name: "V2Empty", template: "<div>{{ message }}</div>", props: ["message"] },
};

describe("schemas list page", () => {
  beforeEach(() => {
    // Reset the global ts-injecty container so each test's useResolveMock wins
    // (the container caches resolved singletons by class name across tests).
    Container.dispose();
    setActivePinia(createPinia());
    useWorkspaces().saveWorkspaces([new Workspace("w-1", "ws")]);
    useWorkspaces().saveSelectedWorkspace(new Workspace("w-1", "ws"));
    vi.mocked(useEnsureWorkspacesModule.useEnsureWorkspaces).mockReturnValue({
      ensureWorkspaces: vi.fn(async () => {}),
      selectedWorkspace: ref(null),
    } as never);
  });

  it("loads schemas for the selected workspace and renders a row per schema", async () => {
    const execute = vi.fn(async () => [SCHEMA]);
    useResolveMock(GetSchemasUseCase, { execute });

    const wrapper = shallowMount(SchemasPage, { global: { stubs } });
    await flushPromises();

    expect(execute).toHaveBeenCalledWith("w-1");
    expect(wrapper.text()).toContain("sample_size");
  });

  it("shows the empty state when the workspace has no schemas", async () => {
    useResolveMock(GetSchemasUseCase, { execute: vi.fn(async () => []) });

    const wrapper = shallowMount(SchemasPage, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toContain("schemas.empty");
  });

  it("hydrates workspaces and renders the app header on mount", async () => {
    const ensureWorkspaces = vi.fn(async () => {});
    vi.mocked(useEnsureWorkspacesModule.useEnsureWorkspaces).mockReturnValue({
      ensureWorkspaces,
      selectedWorkspace: ref(null),
    } as never);
    useResolveMock(GetSchemasUseCase, { execute: vi.fn(async () => []) });

    const wrapper = shallowMount(SchemasPage, { global: { stubs } });
    await flushPromises();

    expect(ensureWorkspaces).toHaveBeenCalledOnce();
    expect(wrapper.findComponent({ name: "AppHeader" }).exists()).toBe(true);
  });
});
