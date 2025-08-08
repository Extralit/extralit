<template>
  <div v-if="!progress" :style="{ width: `${size}px`, height: `${size}px` }" class="spinner"></div>
  <div v-else class="spinner--progress" :style="{ width: `${size}px`, height: `${size}px` }">
    <div class="spinner--progress__circle">
      <div
        class="spinner--progress__progress"
        :style="{
          'background-image': `conic-gradient(${progressColor} ${progress * 3.6}deg,rgb(0 0 0 / 10%) 0deg)`,
        }"
      ></div>
    </div>
  </div>
</template>

<script>
export default {
  name: "BaseSpinnerComponent",
  props: {
    progress: {
      type: Number,
      default: 0,
    },
    progressColor: {
      type: String,
      default: "#000000de",
    },
    size: {
      type: Number,
      default: 32,
    },
  },
};
</script>

<style lang="scss" scoped>
.spinner {
  width: $base-space * 4;
  height: $base-space * 4;
  border-radius: 50%;
  border: 5px solid var(--color-brand-secondary);
  border-top-color: transparent;
  animation-name: spin;
  animation-iteration-count: infinite;
  animation-timing-function: linear;
  animation-duration: 1s;
  &--progress {
    display: flex;
    justify-content: center;
    align-items: center;
    animation: none;
    border: none !important;
    &__circle {
      position: relative;
      width: 100%;
      height: 100%;
      border-radius: 50%;
    }
    &__progress {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      box-sizing: border-box;
      mask: radial-gradient(farthest-side, transparent calc(100% - 3px), var(--color-white) calc(100% - 3px + 1px));
    }
  }
}
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
