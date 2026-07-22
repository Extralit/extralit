import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

const executeMock = vi.fn();
vi.mock("ts-injecty", () => ({
  useResolve: () => ({ execute: executeMock }),
}));

import { useExtractionsViewModel } from "./useExtractionsViewModel";

describe("useExtractionsViewModel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    executeMock.mockReset();
  });

  it("loads the projection for the override workspace id", async () => {
    const projection = new WorkspaceProjection([], [], 0);
    executeMock.mockResolvedValue(projection);

    const vm = useExtractionsViewModel("w-1");
    await vm.load();

    expect(executeMock).toHaveBeenCalledWith("w-1");
    expect(vm.projection.value).toBe(projection);
    expect(vm.loadFailed.value).toBe(false);
    expect(vm.isLoading.value).toBe(false);
  });

  it("does nothing without a workspace id", async () => {
    const vm = useExtractionsViewModel(null);
    await vm.load();
    expect(executeMock).not.toHaveBeenCalled();
  });

  it("flags load failure", async () => {
    executeMock.mockRejectedValue(new Error("boom"));
    const vm = useExtractionsViewModel("w-1");
    await vm.load();
    expect(vm.loadFailed.value).toBe(true);
  });

  it("builds the annotation URL on cell click but does not navigate (guard off)", () => {
    const vm = useExtractionsViewModel("w-1");
    const url = vm.onCellClick({ schemaId: "s-1", reference: "10.1/a b" });
    expect(url).toBe("/dataset/s-1/annotation-mode?_search=10.1%2Fa%20b");
  });
});
