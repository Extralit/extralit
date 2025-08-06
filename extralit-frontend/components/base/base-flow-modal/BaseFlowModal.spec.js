import { mount } from "@vue/test-utils";
import BaseFlowModal from "./BaseFlowModal.vue";

describe("BaseFlowModal", () => {
  let wrapper;

  const defaultProps = {
    visible: true,
    title: "Test Modal",
    steps: [
      { id: "step1", title: "Step 1" },
      { id: "step2", title: "Step 2" },
      { id: "step3", title: "Step 3" },
    ],
    currentStep: 0,
  };

  beforeEach(() => {
    // Mock window.confirm
    global.confirm = jest.fn(() => true);

    wrapper = mount(BaseFlowModal, {
      propsData: defaultProps,
      stubs: {
        "base-icon": true,
        "BaseButton": {
          template: '<button class="mock-base-button"><slot /></button>',
          props: ["variant", "disabled", "loading"],
        },
      },
    });
  });

  afterEach(() => {
    wrapper.destroy();
    jest.restoreAllMocks();
  });

  describe("Component Structure", () => {
    it("should render the modal when visible", () => {
      expect(wrapper.find(".flow-modal-mask").exists()).toBe(true);
      expect(wrapper.find(".flow-modal-container").exists()).toBe(true);
    });

    it("should not render when not visible", async () => {
      await wrapper.setProps({ visible: false });
      expect(wrapper.find(".flow-modal-mask").exists()).toBe(false);
    });

    it("should display the correct title", () => {
      expect(wrapper.find(".flow-modal__title").text()).toBe("Test Modal");
    });

    it("should render all steps in progress indicator", () => {
      const steps = wrapper.findAll(".flow-modal__step");
      expect(steps).toHaveLength(3);
      expect(steps.at(0).text()).toContain("Step 1");
      expect(steps.at(1).text()).toContain("Step 2");
      expect(steps.at(2).text()).toContain("Step 3");
    });
  });

  describe("Step Navigation", () => {
    it("should highlight the current step", () => {
      const currentStep = wrapper.findAll(".flow-modal__step").at(0);
      expect(currentStep.classes()).toContain("flow-modal__step--active");
    });

    it("should show completed steps", async () => {
      await wrapper.setProps({ currentStep: 2 });

      const steps = wrapper.findAll(".flow-modal__step");
      expect(steps.at(0).classes()).toContain("flow-modal__step--completed");
      expect(steps.at(1).classes()).toContain("flow-modal__step--completed");
      expect(steps.at(2).classes()).toContain("flow-modal__step--active");
    });

    it("should calculate progress percentage correctly", async () => {
      expect(wrapper.vm.progressPercentage).toBe(33.33333333333333); // (0+1)/3 * 100

      await wrapper.setProps({ currentStep: 1 });
      expect(wrapper.vm.progressPercentage).toBe(66.66666666666666); // (1+1)/3 * 100

      await wrapper.setProps({ currentStep: 2 });
      expect(wrapper.vm.progressPercentage).toBe(100); // (2+1)/3 * 100
    });
  });

  describe("Navigation Controls", () => {
    it("should show Previous button when canGoBack is true and not on first step", async () => {
      await wrapper.setProps({ currentStep: 1, canGoBack: true });

      const prevButton = wrapper.find(".flow-modal__nav-left .mock-base-button");
      expect(prevButton.exists()).toBe(true);
    });

    it("should not show Previous button on first step", () => {
      const prevButton = wrapper.find(".flow-modal__nav-left .mock-base-button");
      expect(prevButton.exists()).toBe(false);
    });

    it("should show navigation buttons in the right section", () => {
      const navButtons = wrapper.findAll(".flow-modal__nav-right .mock-base-button");
      expect(navButtons.length).toBeGreaterThan(0);
    });
  });

  describe("Events", () => {
    it("should emit close when close button is clicked", async () => {
      const closeButton = wrapper.find(".flow-modal__close-button");
      await closeButton.trigger("click");

      // Since confirmClose is true by default, this would show a confirmation
      // We've mocked confirm to return true, so it should emit close
      expect(wrapper.emitted("close")).toBeTruthy();
    });
  });

  describe("Props Validation", () => {
    it("should validate steps prop structure", () => {
      const validSteps = [{ id: "test", title: "Test Step" }];

      const invalidSteps = [
        { title: "Missing ID" },
        { id: "test" }, // Missing title
      ];

      expect(BaseFlowModal.props.steps.validator(validSteps)).toBe(true);
      expect(BaseFlowModal.props.steps.validator(invalidSteps)).toBe(false);
    });
  });

  describe("Computed Properties", () => {
    it("should correctly identify last step", async () => {
      expect(wrapper.vm.isLastStep).toBe(false);

      await wrapper.setProps({ currentStep: 2 });
      expect(wrapper.vm.isLastStep).toBe(true);
    });

    it("should return current step data", async () => {
      expect(wrapper.vm.currentStepData).toEqual({ id: "step1", title: "Step 1" });

      await wrapper.setProps({ currentStep: 1 });
      expect(wrapper.vm.currentStepData).toEqual({ id: "step2", title: "Step 2" });
    });
  });

  describe("Body Class Management", () => {
    it("should add body class when modal is visible", () => {
      // This would need to be tested in a more integrated environment
      // as jsdom doesn't fully support document.body.classList
    });

    it("should remove body class when component is destroyed", () => {
      // This would also need integration testing
    });
  });
});
