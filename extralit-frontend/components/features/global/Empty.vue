<template>
  <div class="empty-state">
    <slot>
      <p class="empty-state__message" v-text="message" />
    </slot>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "Empty",
  props: { message: { type: String, default: "" } },
});
</script>

<style lang="scss" scoped>
.empty-state {
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
