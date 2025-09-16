<template>
  <BaseButton class="button-extralit-hub" @click="$emit('click')">
    <brand-icon class="brand-icon" color="white" aria-label="Extralit icon" />
    {{ $t("button.extralithub-login") }}
  </BaseButton>
</template>

<script>
export default {
  name: "ExtralitHubButton",
};
</script>

<style lang="scss" scoped>
.button-extralit-hub {
  @extend %button !optional;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: var(--color-white);
  width: 100%;
  min-height: $base-space * 6;
  padding: calc($base-space / 2) $base-space * 4;
  justify-content: center;
  border: none;
  transition: all 0.3s ease;

  &:hover {
    background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  &:active {
    transform: translateY(0);
  }

  svg {
    width: 30px;
    height: auto;
    margin-right: $base-space;
  }
}
</style>
