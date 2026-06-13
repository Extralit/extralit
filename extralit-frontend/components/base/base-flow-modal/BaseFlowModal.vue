<template>
  <div v-if="visible" class="flow-modal-mask">
    <div class="flow-modal-container">
      <!-- Header -->
      <div class="flow-modal__header">
        <div class="flow-modal__header-content">
          <h2 class="flow-modal__title">{{ title }}</h2>
          <button v-if="canClose" class="flow-modal__close-button" @click="handleClose">×</button>
        </div>

        <!-- Progress Indicator -->
        <div v-if="steps.length > 1" class="flow-modal__progress">
          <div class="flow-modal__progress-bar">
            <div class="flow-modal__progress-fill" :style="{ width: progressPercentage + '%' }"></div>
          </div>
          <div class="flow-modal__steps">
            <div
              v-for="(step, index) in steps"
              :key="step.id"
              class="flow-modal__step"
              :class="{
                'flow-modal__step--active': index === currentStep,
                'flow-modal__step--completed': index < currentStep,
                'flow-modal__step--optional': step.optional,
              }"
            >
              <div class="flow-modal__step-indicator">
                <span v-if="index < currentStep" class="flow-modal__step-icon">✓</span>
                <span v-else class="flow-modal__step-number">{{ index + 1 }}</span>
              </div>
              <span class="flow-modal__step-title">{{ step.title }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Content Area -->
      <div class="flow-modal__content">
        <div class="flow-modal__content-inner">
          <slot :current-step="currentStep" :step-data="stepData" />
        </div>
      </div>

      <!-- Footer Navigation -->
      <div class="flow-modal__footer">
        <div class="flow-modal__navigation">
          <div class="flow-modal__nav-left">
            <BaseButton
              v-if="canGoBack && currentStep > 0"
              class="secondary"
              :disabled="loading"
              @click="handlePrevious"
            >
              Previous
            </BaseButton>
          </div>

          <div class="flow-modal__nav-right">
            <BaseButton v-if="showCancelButton" class="secondary outline" :disabled="loading" @click="handleCancel">
              Cancel
            </BaseButton>

            <BaseButton
              v-if="!isLastStep"
              class="primary"
              :disabled="!canGoNext || loading"
              :loading="loading"
              @click="handleNext"
            >
              {{ getNextButtonText() }}
            </BaseButton>

            <BaseButton
              v-if="isLastStep"
              class="primary"
              :disabled="!canComplete || loading"
              :loading="loading"
              @click="handleComplete"
            >
              {{ completeButtonText || "Finish" }}
            </BaseButton>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: "BaseFlowModal",

  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      required: true,
    },
    steps: {
      type: Array,
      required: true,
      validator: (steps) => {
        return steps.every(
          (step) => step.id && step.title && typeof step.id === "string" && typeof step.title === "string"
        );
      },
    },
    currentStep: {
      type: Number,
      default: 0,
    },
    canGoBack: {
      type: Boolean,
      default: true,
    },
    canGoNext: {
      type: Boolean,
      default: true,
    },
    canClose: {
      type: Boolean,
      default: true,
    },
    canComplete: {
      type: Boolean,
      default: true,
    },
    confirmClose: {
      type: Boolean,
      default: true,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    stepData: {
      type: Object,
      default: () => ({}),
    },
    showCancelButton: {
      type: Boolean,
      default: true,
    },
    completeButtonText: {
      type: String,
      default: null,
    },
    nextButtonText: {
      type: String,
      default: "Next",
    },
    submitStepIndex: {
      type: Number,
      default: null,
    },
  },

  computed: {
    progressPercentage() {
      if (this.steps.length <= 1) return 100;
      return ((this.currentStep + 1) / this.steps.length) * 100;
    },

    isLastStep() {
      return this.currentStep === this.steps.length - 1;
    },

    currentStepData() {
      return this.steps[this.currentStep] || {};
    },
  },

  watch: {
    visible(newValue) {
      if (newValue) {
        document.body.classList.add("flow-modal-open");
      } else {
        document.body.classList.remove("flow-modal-open");
      }
    },
  },

  beforeUnmount() {
    document.body.classList.remove("flow-modal-open");
  },

  methods: {
    handlePrevious() {
      if (this.currentStep > 0 && !this.loading) {
        this.$emit("step-change", this.currentStep - 1);
      }
    },

    handleNext() {
      if (!this.isLastStep && this.canGoNext && !this.loading) {
        this.$emit("validate-step", {
          step: this.currentStep,
          callback: (isValid) => {
            if (isValid) {
              this.$emit("step-change", this.currentStep + 1);
            }
          },
        });
      }
    },

    handleComplete() {
      if (this.canComplete && !this.loading) {
        this.$emit("validate-step", {
          step: this.currentStep,
          callback: (isValid) => {
            if (isValid) {
              this.$emit("complete");
            }
          },
        });
      }
    },

    handleCancel() {
      if (this.confirmClose) {
        this.showCancelConfirmation();
      } else {
        this.$emit("cancel");
      }
    },

    handleClose() {
      if (this.confirmClose) {
        this.showCloseConfirmation();
      } else {
        this.$emit("close");
      }
    },

    showCancelConfirmation() {
      if (confirm(this.$t("button.confirmCancel"))) {
        this.$emit("cancel");
      }
    },

    showCloseConfirmation() {
      if (confirm(this.$t("button.confirmCancel"))) {
        this.$emit("close");
      }
    },

    getNextButtonText() {
      if (this.submitStepIndex !== null && this.currentStep === this.submitStepIndex) {
        return "Submit";
      }
      return this.nextButtonText;
    },
  },
};
</script>

<style lang="scss" scoped>
.flow-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  background: var(--bg-opacity-54);
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}

.flow-modal-container {
  width: 100%;
  height: 100vh;
  max-width: 100%;
  background: var(--bg-accent-grey-1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.flow-modal__header {
  flex-shrink: 0;
  background: var(--bg-accent-grey-1);
  border-bottom: 1px solid var(--border-field);
  padding: $base-space * 3;
}

.flow-modal__header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $base-space * 2;
}

.flow-modal__title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--fg-primary);
  margin: 0;
}

.flow-modal__close-button {
  padding: $base-space;
  min-width: auto;
  background: none;
  border: none;
  color: var(--fg-secondary);

  &:hover {
    color: var(--fg-primary);
    background: var(--bg-opacity-6);
  }
}

.flow-modal__progress {
  margin-top: $base-space * 2;
}

.flow-modal__progress-bar {
  width: 100%;
  height: 4px;
  background: var(--bg-opacity-10);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: $base-space * 3;
}

.flow-modal__progress-fill {
  height: 100%;
  background: var(--bg-action);
  transition: width 0.3s ease;
}

.flow-modal__steps {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $base-space * 2;

  @include media("<tablet") {
    flex-wrap: wrap;
    gap: $base-space;
  }
}

.flow-modal__step {
  display: flex;
  align-items: center;
  gap: $base-space;
  flex: 1;
  min-width: 0;

  @include media("<tablet") {
    flex: none;
    min-width: auto;
  }
}

.flow-modal__step-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-opacity-10);
  color: var(--fg-secondary);
  font-weight: 600;
  font-size: 0.9rem;
  flex-shrink: 0;
  transition: all 0.2s ease;

  .flow-modal__step--active & {
    background: var(--bg-action);
    color: var(--color-white);
  }

  .flow-modal__step--completed & {
    background: var(--color-success);
    color: var(--color-white);
  }
}

.flow-modal__step-icon {
  font-size: 1rem;
}

.flow-modal__step-number {
  font-size: 0.9rem;
}

.flow-modal__step-title {
  font-size: 0.9rem;
  color: var(--fg-secondary);
  font-weight: 500;

  .flow-modal__step--active & {
    color: var(--fg-primary);
    font-weight: 600;
  }

  .flow-modal__step--completed & {
    color: var(--fg-primary);
  }

  .flow-modal__step--optional & {
    font-style: italic;
  }

  @include media("<tablet") {
    display: none;
  }
}

.flow-modal__content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.flow-modal__content-inner {
  flex: 1;
  overflow: auto;
  padding: $base-space * 3;
}

.flow-modal__footer {
  flex-shrink: 0;
  background: var(--bg-accent-grey-2);
  border-top: 1px solid var(--border-field);
  padding: $base-space * 3;
}

.flow-modal__navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.flow-modal__nav-left,
.flow-modal__nav-right {
  display: flex;
  gap: $base-space * 2;
  align-items: center;
}

// Transitions
.flow-modal-enter-active,
.flow-modal-leave-active {
  transition: opacity 0.3s ease;
}

.flow-modal-enter,
.flow-modal-leave-to {
  opacity: 0;
}

.flow-modal-enter .flow-modal-container,
.flow-modal-leave-to .flow-modal-container {
  transform: scale(0.95);
}

// Global body class to prevent scrolling
:global(.flow-modal-open) {
  overflow: hidden;
}

// Responsive adjustments
@include media("<tablet") {
  .flow-modal__header,
  .flow-modal__content-inner,
  .flow-modal__footer {
    padding: $base-space * 2;
  }

  .flow-modal__title {
    font-size: 1.25rem;
  }

  .flow-modal__nav-left,
  .flow-modal__nav-right {
    gap: $base-space;
  }
}
</style>
