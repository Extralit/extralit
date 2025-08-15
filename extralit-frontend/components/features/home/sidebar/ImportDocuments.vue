<template>
  <div class="import-documents">
    <BaseButton class="import-documents__button" @click="handleClick">
      <svgicon
        class="import-documents__button__icon"
        name="import"
        width="18"
        height="18"
        color="var(--bg-opacity-87)"
        aria-hidden="true"
      />
      {{ $t("home.importDocuments") }}
    </BaseButton>
  </div>
</template>

<script>
import "assets/icons/import";

export default {
  name: "ImportDocuments",
  emits: ["on-click"],
  methods: {
    handleClick() {
      this.$emit("on-click");
    },
  },
};
</script>

<style lang="scss" scoped>
.import-documents {
  &__button.button {
    min-height: 42px;
    color: var(--fg-primary);
    background: linear-gradient(177.33deg, var(--bg-accent-grey-5) 20%, var(--bg-opacity-4) 100%);
    box-shadow: 0 0 0 1px var(--bg-opacity-10);

    &:hover {
      background: linear-gradient(177.33deg, var(--bg-accent-grey-5) 20%, var(--bg-opacity-2) 100%);
    }
  }

  &__button__icon {
    flex-shrink: 0;
  }
}
</style>
