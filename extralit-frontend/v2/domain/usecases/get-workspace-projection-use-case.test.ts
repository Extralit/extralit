import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GetWorkspaceProjectionUseCase, PROJECTION_PAGE_SIZE } from "./get-workspace-projection-use-case";
import { useExtractions } from "~/v2/infrastructure/storage/ExtractionsStorage";

const COLUMN = {
  name: "Design.type",
  schemaId: "s-1",
  schemaName: "Design",
  questionName: "type",
  subColumn: null,
  dtype: "text",
};

const row = (reference: string) => ({ reference, rowIndex: 0, cells: {} });

describe("GetWorkspaceProjectionUseCase", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads every page into one projection and saves it to storage", async () => {
    const repository = {
      getWorkspaceProjection: vi
        .fn()
        .mockResolvedValueOnce({ columns: [COLUMN], rows: [row("10.1/a")], totalReferences: 150 })
        .mockResolvedValueOnce({ columns: [COLUMN], rows: [row("10.1/b")], totalReferences: 150 }),
    };
    const useCase = new GetWorkspaceProjectionUseCase(repository as never, useExtractions());

    const projection = await useCase.execute("w-1");

    expect(repository.getWorkspaceProjection).toHaveBeenNthCalledWith(1, "w-1", 0, PROJECTION_PAGE_SIZE);
    expect(repository.getWorkspaceProjection).toHaveBeenNthCalledWith(2, "w-1", 100, PROJECTION_PAGE_SIZE);
    expect(repository.getWorkspaceProjection).toHaveBeenCalledTimes(2);
    expect(projection.rows.map((r) => r.reference)).toEqual(["10.1/a", "10.1/b"]);
    expect(projection.totalReferences).toBe(150);
    expect(useExtractions().get().projection).toEqual(projection);
  });

  it("makes a single call when everything fits in one page", async () => {
    const repository = {
      getWorkspaceProjection: vi
        .fn()
        .mockResolvedValue({ columns: [COLUMN], rows: [row("10.1/a")], totalReferences: 1 }),
    };
    const useCase = new GetWorkspaceProjectionUseCase(repository as never, useExtractions());
    await useCase.execute("w-1");
    expect(repository.getWorkspaceProjection).toHaveBeenCalledTimes(1);
  });
});
