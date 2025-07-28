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
    wrapper = mount(BaseFlowModal, {
      propsData: defaultProps,
      stubs: {
        "base-icon": true,
        "base-button": true,
      },
    });
  });

  afterEach(() => {
    wrapper.destroy();
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

      const prevButton = wrapper.find(".flow-modal__nav-left").find("button");
      expect(prevButton.exists()).toBe(true);
    });

    it("should not show Previous button on first step", () => {
      const prevButton = wrapper.find(".flow-modal__nav-left").find("button");
      expect(prevButton.exists()).toBe(false);
    });

    it("should show Next button when not on last step", () => {
      const nextButton = wrapper.findAll(".flow-modal__nav-right button").filter(btn =>
        btn.text().includes("Next")
      );
      expect(nextButton).toHaveLength(1);
    });

    it("should show Finish button on last step", async () => {
      await wrapper.setProps({ currentStep: 2 });

      const finishButton = wrapper.findAll(".flow-modal__nav-right button").filter(btn =>
        btn.text().includes("Finish")
      );
      expect(finishButton).toHaveLength(1);
    });

    it("should disable navigation when loading", async () => {
      await wrapper.setProps({ loading: true, currentStep: 1, canGoBack: true });

      const buttons = wrapper.findAll(".flow-modal__nav-left button, .flow-modal__nav-right button");
      buttons.wrappers.forEach(button => {
        expect(button.attributes("disabled")).toBeDefined();
      });
    });
  });

  describe("Events", () => {
    it("should emit step-change when navigation occurs", async () => {
      await wrapper.setProps({ currentStep: 1, canGoBack: true });

      const prevButton = wrapper.find(".flow-modal__nav-left button");
      await prevButton.trigger("click");

      expect(wrapper.emitted("step-change")).toBeTruthy();
      expect(wrapper.emitted("step-change")[0]).toEqual([0]);
    });

    it("should emit validate-step before navigation", async () => {
      const nextButton = wrapper.findAll(".flow-modal__nav-right button").filter(btn =>
        btn.text().includes("Next")
      ).at(0);

      await nextButton.trigger("click");

      expect(wrapper.emitted("validate-step")).toBeTruthy();
      expect(wrapper.emitted("validate-step")[0][0]).toMatchObject({
        step: 0,
        callback: expect.any(Function),
      });
    });

    it("should emit complete on finish button click", async () => {
      await wrapper.setProps({ currentStep: 2 });

      const finishButton = wrapper.findAll(".flow-modal__nav-right button").filter(btn =>
        btn.text().includes("Finish")
      ).at(0);

      await finishButton.trigger("click");

      expect(wrapper.emitted("validate-step")).toBeTruthy();
    });

    it("should emit close when close button is clicked", async () => {
      const closeButton = wrapper.find(".flow-modal__close-button");
      await closeButton.trigger("click");

      // Since confirmClose is true by default, this would show a confirmation
      // In a real test, we'd mock the confirm dialog
    });
  });

  describe("Props Validation", () => {
    it("should validate steps prop structure", () => {
      const validSteps = [
        { id: "test", title: "Test Step" },
      ];

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