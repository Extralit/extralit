import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import Container from "ts-injecty";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { RebuildSchemaIndexUseCase } from "~/v2/domain/usecases/rebuild-schema-index-use-case";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { useSchemaSettingsViewModel } from "./useSchemaSettingsViewModel";

vi.mock("~/v1/infrastructure/services/useNotifications", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));
// useTranslate calls useNuxtApp() — unavailable in the happy-dom env, so mock it too.
vi.mock("~/v1/infrastructure/services/useTranslate", () => ({
  useTranslate: () => ({ t: (key: string) => key, tc: (key: string) => key }),
}));

const SETTINGS = {
  schema: new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "", ""),
  versions: [],
  questions: [],
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
    useResolveMock(RebuildSchemaIndexUseCase, { execute: vi.fn() });

    const vm = useSchemaSettingsViewModel("s-1");
    await vm.load();

    expect(execute).toHaveBeenCalledWith("s-1");
    expect(vm.settings.value?.schema.name).toBe("sample_size");
  });

  it("rebuild flag toggles around the (possibly slow) rebuild call", async () => {
    useResolveMock(GetSchemaSettingsUseCase, { execute: vi.fn(async () => SETTINGS) });
    let resolveRebuild!: (n: number) => void;
    useResolveMock(RebuildSchemaIndexUseCase, {
      execute: vi.fn(() => new Promise<number>((resolve) => (resolveRebuild = resolve))),
    });

    const vm = useSchemaSettingsViewModel("s-1");
    const pending = vm.rebuildIndex();
    expect(vm.isRebuilding.value).toBe(true);

    resolveRebuild(42);
    await pending;
    expect(vm.isRebuilding.value).toBe(false);
  });
});
