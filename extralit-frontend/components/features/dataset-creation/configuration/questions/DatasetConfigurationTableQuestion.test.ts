import { shallowMount } from "@vue/test-utils";
import DatasetConfigurationTableQuestion from "./DatasetConfigurationTableQuestion.vue";
import { QuestionCreation } from "~/v1/domain/entities/hub/QuestionCreation";
import { Subset } from "~/v1/domain/entities/hub/Subset";

// Mock the Validation component
jest.mock("~/components/features/annotation/settings/Validation.vue", () => ({
  name: "Validation",
  template: '<div class="mock-validation"></div>',
  props: ["validations"],
}));

// Mock SVG icon
jest.mock("assets/icons/close", () => ({}));

describe("DatasetConfigurationTableQuestion", () => {
  let mockSubset: Subset;
  let mockQuestion: QuestionCreation;

  beforeEach(() => {
    // Create a mock subset with required structure
    const datasetInfo = {
      splits: {
        train: {
          name: "train",
          num_examples: 100,
        },
      },
      features: {},
    };

    mockSubset = new Subset("default", datasetInfo);

    // Create a table question
    mockQuestion = new QuestionCreation(
      mockSubset,
      "table_question",
      {
        type: "table",
        options: [
          { name: "column1", title: "Column 1", description: "" },
          { name: "column2", title: "Column 2", description: "" },
        ],
        use_table: true,
      }
    );
  });

  describe("rendering", () => {
    it("renders without crashing", () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      expect(wrapper.exists()).toBe(true);
      expect(wrapper.find(".table-config").exists()).toBe(true);
    });

    it("renders column inputs for each column", () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const columnInputs = wrapper.findAll(".table-config__column");
      expect(columnInputs.length).toBe(2);
    });

    it("renders add column button", () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      expect(wrapper.find(".table-config__add-btn").exists()).toBe(true);
    });

    it("renders remove button for each column when more than one column", () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const removeButtons = wrapper.findAll(".table-config__remove-btn");
      expect(removeButtons.length).toBe(2);
    });

    it("does not render remove button when only one column", () => {
      mockQuestion.settings.options = [
        { name: "column1", title: "Column 1", description: "" },
      ];

      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      expect(wrapper.find(".table-config__remove-btn").exists()).toBe(false);
    });
  });

  describe("column management", () => {
    it("adds a new column when add button is clicked", async () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const addButton = wrapper.find(".table-config__add-btn");
      await addButton.trigger("click");

      expect(mockQuestion.settings.options.length).toBe(3);
      expect(mockQuestion.settings.options[2]).toEqual({
        name: "column3",
        title: "Column 3",
        description: "",
      });
    });

    it("removes a column when remove button is clicked", async () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const removeButtons = wrapper.findAll(".table-config__remove-btn");
      await removeButtons.at(0).trigger("click");

      expect(mockQuestion.settings.options.length).toBe(1);
      expect(mockQuestion.settings.options[0].name).toBe("column2");
    });

    it("updates column name when input changes", async () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const nameInputs = wrapper.findAll(".table-config__input--name");
      const firstNameInput = nameInputs.at(0);

      await firstNameInput.setValue("new_column_name");
      await firstNameInput.trigger("input");

      expect(mockQuestion.settings.options[0].name).toBe("new_column_name");
    });

    it("updates column title when input changes", async () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const titleInputs = wrapper.findAll(".table-config__input--title");
      const firstTitleInput = titleInputs.at(0);

      await firstTitleInput.setValue("New Column Title");
      await firstTitleInput.trigger("input");

      expect(mockQuestion.settings.options[0].title).toBe("New Column Title");
    });
  });

  describe("validation", () => {
    it("displays validation errors when question is invalid", async () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      // Manually clear options and trigger validation to simulate invalid state
      mockQuestion.settings.options = [];
      (wrapper.vm as any).isDirty = true;
      (wrapper.vm as any).validateOptions();

      await wrapper.vm.$nextTick();

      // Verify that the errors state is set with validation messages
      expect((wrapper.vm as any).errors.options.length).toBeGreaterThan(0);
      expect((wrapper.vm as any).errors.options).toContain(
        "datasetCreation.questions.table.atLeastOneColumn"
      );
    });

    it("emits is-focused event on input focus", async () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      // Call onFocus directly since jsdom focus events don't reliably bubble
      (wrapper.vm as any).onFocus();
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted("is-focused")).toBeTruthy();
      expect(wrapper.emitted("is-focused")[0]).toEqual([true]);
    });

    it("emits is-focused false on input blur", async () => {
      const wrapper = shallowMount(DatasetConfigurationTableQuestion, {
        propsData: {
          question: mockQuestion,
        },
        mocks: {
          $t: (key: string) => key,
        },
      });

      const input = wrapper.find(".table-config__input");
      await input.trigger("blur");

      expect(wrapper.emitted("is-focused")).toBeTruthy();
      expect(wrapper.emitted("is-focused")[0]).toEqual([false]);
    });
  });
});
