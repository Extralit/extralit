<template>
  <span class="load-line" :style="{ minWidth: 100, background: color, height: height }"></span>
</template>

<script>
export default {
  props: {
    color: {
      type: String,
      default: "#3e5cc9",
    },
    height: {
      type: String,
      default: "2px",
    },
  },
};
</script>

<style lang="scss" scoped>
.load-line {
  position: absolute;
  width: 100%;
  animation: load 0.8s ease-in-out infinite;
}
@keyframes load {
  0% {
    width: 0%;
  }
  100% {
    width: 100%;
  }
}
</style>
