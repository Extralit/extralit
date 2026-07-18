import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import Container from "ts-injecty";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import SchemasPage from "./index.vue";

const SCHEMA = new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "2026-01-01", "2026-01-01");

describe("schemas list page", () => {
  beforeEach(() => {
    // Reset the global ts-injecty container so each test's useResolveMock wins
    // (the container caches resolved singletons by class name across tests).
    Container.dispose();
    setActivePinia(createPinia());
    useWorkspaces().saveWorkspaces([new Workspace("w-1", "ws")]);
    useWorkspaces().saveSelectedWorkspace(new Workspace("w-1", "ws"));
  });

  it("loads schemas for the selected workspace and renders a row per schema", async () => {
    const execute = vi.fn(async () => [SCHEMA]);
    useResolveMock(GetSchemasUseCase, { execute });

    const wrapper = shallowMount(SchemasPage, { global: { stubs: { NuxtLink: { template: "<a><slot /></a>" } } } });
    await flushPromises();

    expect(execute).toHaveBeenCalledWith("w-1");
    expect(wrapper.text()).toContain("sample_size");
  });

  it("shows the empty state when the workspace has no schemas", async () => {
    useResolveMock(GetSchemasUseCase, { execute: vi.fn(async () => []) });

    const wrapper = shallowMount(SchemasPage, { global: { stubs: { NuxtLink: true } } });
    await flushPromises();

    expect(wrapper.text()).toContain("schemas.empty");
  });
});
