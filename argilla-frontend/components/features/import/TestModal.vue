<template>
  <div
    v-if="visible"
    style="
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 255, 0.8);
      z-index: 999999;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 24px;
      font-weight: bold;
    "
  >
    <div style="text-align: center;">
      <h2>TEST MODAL WORKING!</h2>
      <p>Visible: {{ visible }}</p>
      <button @click="$emit('close')" style="padding: 10px 20px; font-size: 16px; background: white; color: black; border: none; border-radius: 4px; cursor: pointer;">
        Close Modal
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: "TestModal",
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
  },
  watch: {
    visible(newValue) {
      console.log("TestModal visible changed to:", newValue);
    },
  },
  mounted() {
    console.log("TestModal mounted, visible:", this.visible);
  },
};
</script>