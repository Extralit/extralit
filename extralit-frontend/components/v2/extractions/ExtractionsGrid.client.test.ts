import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import ExtractionsGrid from "./ExtractionsGrid.client.vue";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

const tableSpy = vi.fn(async (data: unknown) => ({ __data: data, delete: async () => undefined }));
const initSpy = vi.fn(async () => ({ worker: async () => ({ table: tableSpy }) }));

vi.mock("~/components/v2/extractions/perspective-bootstrap", () => ({
  initPerspective: (...args: unknown[]) => initSpy(...args),
}));

const PROJECTION = new WorkspaceProjection(
  [
    {
      name: "Design.type",
      schemaId: "s-1",
      schemaName: "Design",
      questionName: "type",
      subColumn: null,
      dtype: "text",
    },
  ],
  [
    {
      reference: "10.1/a",
      rowIndex: 0,
      cells: {
        "Design.type": { value: "RCT", source: "response", recordId: "r-1", agent: null, score: null },
      },
    },
  ],
  1
);

describe("ExtractionsGrid", () => {
  it("boots perspective once and loads the flat projection rows into a table", async () => {
    mount(ExtractionsGrid, {
      props: { projection: PROJECTION },
      global: {
        config: { compilerOptions: { isCustomElement: (tag: string) => tag.startsWith("perspective-") } },
      },
    });
    await flushPromises();

    expect(initSpy).toHaveBeenCalledTimes(1);
    expect(tableSpy).toHaveBeenCalledWith([{ reference: "10.1/a", "Design.type": "RCT" }]);
  });
});
