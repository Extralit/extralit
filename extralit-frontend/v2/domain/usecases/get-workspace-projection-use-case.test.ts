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

// Deliberately reverse-alphabetical so a `.sort()` regression on the manifest would be caught.
const COLUMN_ZEBRA = {
  name: "Zebra.count",
  schemaId: "s-2",
  schemaName: "Zebra",
  questionName: "count",
  subColumn: null,
  dtype: "number",
};
const COLUMN_APPLE = {
  name: "Apple.type",
  schemaId: "s-3",
  schemaName: "Apple",
  questionName: "type",
  subColumn: null,
  dtype: "text",
};
const SERVER_ORDER_COLUMNS = [COLUMN_ZEBRA, COLUMN_APPLE];

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

  it("aggregates the manifest once, in server order, never sorted or duplicated", async () => {
    const repository = {
      getWorkspaceProjection: vi
        .fn()
        .mockResolvedValueOnce({ columns: SERVER_ORDER_COLUMNS, rows: [row("10.1/a")], totalReferences: 150 })
        .mockResolvedValueOnce({ columns: SERVER_ORDER_COLUMNS, rows: [row("10.1/b")], totalReferences: 150 }),
    };
    const useCase = new GetWorkspaceProjectionUseCase(repository as never, useExtractions());

    const projection = await useCase.execute("w-1");

    expect(projection.columns).toEqual(SERVER_ORDER_COLUMNS);
  });

  it("stops after a single call on a zero-progress response instead of hanging", async () => {
    const repository = {
      getWorkspaceProjection: vi.fn().mockResolvedValue({ columns: [COLUMN], rows: [], totalReferences: 999999 }),
    };
    const useCase = new GetWorkspaceProjectionUseCase(repository as never, useExtractions());

    const projection = await useCase.execute("w-1");

    expect(repository.getWorkspaceProjection).toHaveBeenCalledTimes(1);
    expect(projection.rows).toEqual([]);
  });
});
