import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import Container from "ts-injecty";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemaRecordsUseCase } from "~/v2/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v2/domain/usecases/search-records-use-case";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { RecordsPage } from "~/v2/domain/entities/record/RecordsPage";
import { V2Record } from "~/v2/domain/entities/record/V2Record";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { SchemaVersion } from "~/v2/domain/entities/schema/SchemaVersion";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import { SearchCriteria } from "~/v2/domain/entities/search/SearchCriteria";
import { useSchemaRecordsViewModel } from "./useSchemaRecordsViewModel";

const RECORD = new V2Record("r-1", "s-1", "10.1000/j.x", null, { title: "A study" }, null, "pending", "", "");
const SETTINGS = {
  schema: new Schema("s-1", "sample_size", "ready", "w-1", "v-1", {}, "", ""),
  versions: [new SchemaVersion("v-1", "s-1", 1, "")],
  questions: [],
  columns: [new ColumnMeta("title", "str", false, null)],
};

describe("useSchemaRecordsViewModel", () => {
  beforeEach(() => {
    // Reset the global ts-injecty container so each test's useResolveMock wins
    // (the container caches resolved singletons by class name across tests).
    Container.dispose();
    setActivePinia(createPinia());
  });

  it("lists via GET when there is no query, searches via :search when there is", async () => {
    const list = vi.fn(async () => new RecordsPage([RECORD], 1));
    const search = vi.fn(async () => new RecordsPage([RECORD], 1));
    useResolveMock(GetSchemaRecordsUseCase, { execute: list });
    useResolveMock(SearchRecordsUseCase, { execute: search });
    useResolveMock(GetSchemaSettingsUseCase, { execute: vi.fn(async () => SETTINGS) });

    const vm = useSchemaRecordsViewModel("s-1");
    await vm.search();
    expect(list).toHaveBeenCalledWith("s-1", { offset: 0, limit: 25 });

    vm.searchText.value = "malaria";
    await vm.search();
    expect(search).toHaveBeenCalled();
    expect((search.mock.calls[0] as unknown as [string, SearchCriteria])[1].toQueryBody().query).toEqual({
      text: { q: "malaria" },
    });
  });

  it("passes the status filter through the search path", async () => {
    const search = vi.fn(async () => new RecordsPage([], 0));
    useResolveMock(GetSchemaRecordsUseCase, { execute: vi.fn(async () => new RecordsPage([], 0)) });
    useResolveMock(SearchRecordsUseCase, { execute: search });
    useResolveMock(GetSchemaSettingsUseCase, { execute: vi.fn(async () => SETTINGS) });

    const vm = useSchemaRecordsViewModel("s-1");
    vm.statusFilter.value = "pending";
    await vm.search();

    expect((search.mock.calls[0] as unknown as [string, SearchCriteria])[1].toQueryBody().filters).toEqual({
      and: [{ type: "terms", scope: { entity: "record", property: "status" }, values: ["pending"] }],
    });
  });
});
