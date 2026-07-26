<template>
  <div class="v2-empty">
    <slot>
      <p class="v2-empty__message" v-text="message" />
    </slot>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "V2Empty",
  props: { message: { type: String, default: "" } },
});
</script>

<style lang="scss" scoped>
.v2-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $base-space * 6 $base-space * 2;
  &__message {
    margin: 0;
    color: var(--fg-tertiary);
    @include font-size(14px);
  }
}
</style>
