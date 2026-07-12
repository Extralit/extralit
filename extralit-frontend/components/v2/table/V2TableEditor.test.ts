import { beforeEach, describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { TabulatorFull } from "tabulator-tables";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import V2TableEditor, { tabulatorColumns, valueFromRowData } from "./V2TableEditor.vue";

// The vitest alias resolves tabulator-tables to __mocks__/tabulator-tables.js, which adds
// these static test hooks; the real @types don't declare them, so view them through a cast.
const MockTabulator = TabulatorFull as unknown as {
  constructed: number;
  latest: { emit(event: string, ...args: unknown[]): void } | null;
};

describe("V2TableEditor column derivation", () => {
  it("derives one tabulator column per bound ColumnMeta with dtype-driven editors", () => {
    const columns = tabulatorColumns(
      [
        new ColumnMeta("name", "str", false, null),
        new ColumnMeta("count", "int64", false, null),
        new ColumnMeta("done", "bool", false, null),
        new ColumnMeta("when", "datetime64[ns]", true, null),
      ],
      true
    );

    expect(columns.map((c) => [c.field, c.editor])).toEqual([
      ["name", "input"],
      ["count", "number"],
      ["done", "tickCross"],
      ["when", "date"],
    ]);
  });

  it("honors the review overlay hint over the dtype default", () => {
    const columns = tabulatorColumns([new ColumnMeta("count", "int64", false, { type: "text" })], true);
    expect(columns[0].editor).toBe("input");
  });

  it("disables editors when not editable", () => {
    const columns = tabulatorColumns([new ColumnMeta("name", "str", false, null)], false);
    expect(columns[0].editor).toBe(false);
  });
});

describe("valueFromRowData", () => {
  it("keeps only bound-column keys (server validates keys ⊆ bound columns)", () => {
    const value = valueFromRowData({ name: "a", stray: "x" }, [new ColumnMeta("name", "str", false, null)]);
    expect(value).toEqual({ name: "a" });
  });

  it("drops undefined cells so absent keys stay absent", () => {
    const value = valueFromRowData({ name: undefined }, [new ColumnMeta("name", "str", false, null)]);
    expect(value).toEqual({});
  });
});

describe("V2TableEditor rebuild behavior", () => {
  beforeEach(() => {
    MockTabulator.constructed = 0;
    MockTabulator.latest = null;
  });

  // A v-model parent so a committed cell edit echoes back into modelValue, exercising
  // the self-emit guard that must NOT rebuild the live tabulator (roborev job 148).
  const Parent = defineComponent({
    setup() {
      const value = ref<Record<string, unknown>>({ name: "a" });
      const columns = [new ColumnMeta("name", "str", false, null)];
      return () =>
        h(V2TableEditor, {
          modelValue: value.value,
          columns,
          "onUpdate:modelValue": (v: Record<string, unknown>) => (value.value = v),
        });
    },
  });

  it("does not rebuild the table when the parent echoes back a committed cell edit", async () => {
    const wrapper = mount(Parent);
    await flushPromises();
    expect(MockTabulator.constructed).toBe(1);

    // Simulate a committed cell edit: the stored handler emits the new row value,
    // the parent writes it back into modelValue.
    MockTabulator.latest.emit("cellEdited", { getRow: () => ({ getData: () => ({ name: "b" }) }) });
    await flushPromises();

    // The value round-tripped, but the editor was not torn down and recreated.
    expect(MockTabulator.constructed).toBe(1);
    wrapper.unmount();
  });

  it("rebuilds when modelValue changes externally (draft restore / discard)", async () => {
    const value = ref<Record<string, unknown>>({ name: "a" });
    const columns = [new ColumnMeta("name", "str", false, null)];
    const wrapper = mount(V2TableEditor, { props: { modelValue: value.value, columns } });
    await flushPromises();
    expect(MockTabulator.constructed).toBe(1);

    await wrapper.setProps({ modelValue: { name: "external" } });
    await flushPromises();

    expect(MockTabulator.constructed).toBe(2);
    wrapper.unmount();
  });
});
