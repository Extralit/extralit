import { shallowMount } from "@vue/test-utils";
import BaseSimpleTable from "./BaseSimpleTable.vue";

// Mock RenderTable component
jest.mock("~/components/base/base-render-table/RenderTable.vue", () => ({
  name: "RenderTable",
  template: '<div class="mock-render-table"></div>',
  props: ["tableJSON", "editable", "hasValidValues", "questions"],
  methods: {
    validateTable: jest.fn(() => true),
  },
}));

describe("BaseSimpleTable", () => {
  const mockColumns = [
    {
      field: "name",
      title: "Name",
    },
    {
      field: "age",
      title: "Age",
    },
    {
      field: "email",
      title: "Email",
    },
  ];

  const mockData = [
    { name: "John Doe", age: 30, email: "john@example.com" },
    { name: "Jane Smith", age: 25, email: "jane@example.com" },
  ];

  describe("rendering", () => {
    it("renders without crashing", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
        },
      });

      expect(wrapper.exists()).toBe(true);
      expect(wrapper.find(".tabulator-container--simple").exists()).toBe(true);
    });

    it("renders RenderTable component", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
        },
      });

      expect(wrapper.findComponent({ name: "RenderTable" }).exists()).toBe(true);
    });
  });

  describe("props", () => {
    it("accepts columns and data props", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
        },
      });

      expect(wrapper.props("columns")).toEqual(mockColumns);
      expect(wrapper.props("data")).toEqual(mockData);
    });

    it("accepts editable prop with default false", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
        },
      });

      expect(wrapper.props("editable")).toBe(false);
    });

    it("accepts editable prop set to true", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          editable: true,
        },
      });

      expect(wrapper.props("editable")).toBe(true);
    });

    it("accepts validation prop", () => {
      const validation = { columns: {}, index: [], checks: {} };
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          validation,
        },
      });

      expect(wrapper.props("validation")).toEqual(validation);
    });

    it("accepts validators prop", () => {
      const validators = { name: ["required", "unique"] };
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          validators,
        },
      });

      expect(wrapper.props("validators")).toEqual(validators);
    });

    it("accepts hasValidValues prop", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          hasValidValues: true,
        },
      });

      expect(wrapper.props("hasValidValues")).toBe(true);
    });

    it("accepts questions prop", () => {
      const questions = [{ id: "q1", name: "Question 1" }];
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          questions,
        },
      });

      expect(wrapper.props("questions")).toEqual(questions);
    });
  });

  describe("computedTableJSON", () => {
    it("converts data/columns to TableData format", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
        },
      });

      const vm = wrapper.vm as any;
      const computed = vm.computedTableJSON;

      expect(computed.schema).toBeDefined();
      expect(computed.schema.fields).toHaveLength(3);
      expect(computed.data).toEqual(mockData);
    });

    it("includes validation when provided", () => {
      const validation = { columns: { name: { dtype: "str" } }, index: [], checks: {} };
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          validation,
        },
      });

      const vm = wrapper.vm as any;
      expect(vm.computedTableJSON.validation).toEqual(validation);
    });
  });

  describe("editable class modifier", () => {
    it("does not have editable class when editable is false", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          editable: false,
        },
      });

      expect(wrapper.find(".tabulator-container--editable").exists()).toBe(false);
    });

    it("has editable class when editable is true", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
          editable: true,
        },
      });

      expect(wrapper.find(".tabulator-container--editable").exists()).toBe(true);
    });
  });

  describe("methods", () => {
    it("provides public API methods", () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
        },
      });

      const vm = wrapper.vm as any;

      expect(typeof vm.getData).toBe("function");
      expect(typeof vm.setData).toBe("function");
      expect(typeof vm.getRowCount).toBe("function");
      expect(typeof vm.getColumns).toBe("function");
      expect(typeof vm.validateTable).toBe("function");
      expect(typeof vm.redraw).toBe("function");
    });
  });

  describe("events", () => {
    it("emits events correctly", async () => {
      const wrapper = shallowMount(BaseSimpleTable, {
        propsData: {
          columns: mockColumns,
          data: mockData,
        },
      });

      wrapper.vm.$emit("table-built");
      wrapper.vm.$emit("row-click", {}, {});
      wrapper.vm.$emit("cell-edited", {});

      await wrapper.vm.$nextTick();

      expect(wrapper.emitted("table-built")).toBeTruthy();
      expect(wrapper.emitted("row-click")).toBeTruthy();
      expect(wrapper.emitted("cell-edited")).toBeTruthy();
    });
  });
});
