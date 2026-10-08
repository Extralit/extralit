import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import Container from "ts-injecty";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemaSettingsUseCase } from "~/v1/domain/usecases/get-schema-settings-use-case";
import { Schema } from "~/v1/domain/entities/schema/Schema";
import { useSchemaSettingsViewModel } from "./useSchemaSettingsViewModel";

const SETTINGS = {
  schema: new Schema("s-1", "sample_size", "ready", "w-1", "v-1", {}, "", ""),
  versions: [],
  questions: [],
  columns: [],
};

describe("useSchemaSettingsViewModel", () => {
  beforeEach(() => {
    // Reset the global ts-injecty container so each test's useResolveMock wins
    // (the container caches resolved singletons by class name across tests).
    Container.dispose();
    setActivePinia(createPinia());
  });

  it("loads schema settings on demand", async () => {
    const execute = vi.fn(async () => SETTINGS);
    useResolveMock(GetSchemaSettingsUseCase, { execute });

    const vm = useSchemaSettingsViewModel("s-1");
    await vm.load();

    expect(execute).toHaveBeenCalledWith("s-1");
    expect(vm.settings.value?.schema.name).toBe("sample_size");
  });

  it("sets loadFailed when the settings fetch rejects", async () => {
    useResolveMock(GetSchemaSettingsUseCase, {
      execute: vi.fn(async () => {
        throw new Error("boom");
      }),
    });

    const vm = useSchemaSettingsViewModel("s-1");
    await vm.load();

    expect(vm.loadFailed.value).toBe(true);
    expect(vm.settings.value).toBeNull();
    expect(vm.isLoading.value).toBe(false);
  });
});
