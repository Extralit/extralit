import { shallowMount } from "@vue/test-utils";
import DatasetConfigurationTableField from "./DatasetConfigurationTableField.vue";
import { FieldCreation } from "~/v1/domain/entities/hub/FieldCreation";

describe("DatasetConfigurationTableField", () => {
  let mockField: FieldCreation;

  beforeEach(() => {
    mockField = FieldCreation.from("table_field", "table", "object");
  });

  describe("rendering", () => {
    it("renders without crashing", () => {
      const wrapper = shallowMount(DatasetConfigurationTableField, {
        propsData: {
          field: mockField,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      expect(wrapper.exists()).toBe(true);
      expect(wrapper.find(".table-field-config").exists()).toBe(true);
    });

    it("renders table preview section", () => {
      const wrapper = shallowMount(DatasetConfigurationTableField, {
        propsData: {
          field: mockField,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      expect(wrapper.find(".table-field-config__preview").exists()).toBe(true);
    });

    it("renders preview header with columns", () => {
      const wrapper = shallowMount(DatasetConfigurationTableField, {
        propsData: {
          field: mockField,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const headerCells = wrapper.findAll(
        ".table-field-config__preview-cell--header"
      );
      expect(headerCells.length).toBe(3);
    });

    it("renders preview rows", () => {
      const wrapper = shallowMount(DatasetConfigurationTableField, {
        propsData: {
          field: mockField,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const rows = wrapper.findAll(".table-field-config__preview-row");
      expect(rows.length).toBe(2);
    });

    it("renders help text", () => {
      const wrapper = shallowMount(DatasetConfigurationTableField, {
        propsData: {
          field: mockField,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const helpLabel = wrapper.find(".table-field-config__help");
      expect(helpLabel.exists()).toBe(true);
      expect(helpLabel.text()).toBe("datasetCreation.fields.table.helpText");
    });

    it("renders placeholder cells in preview rows", () => {
      const wrapper = shallowMount(DatasetConfigurationTableField, {
        propsData: {
          field: mockField,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const placeholders = wrapper.findAll(
        ".table-field-config__preview-placeholder"
      );
      // 2 rows × 3 columns = 6 placeholders
      expect(placeholders.length).toBe(6);
    });
  });
});
