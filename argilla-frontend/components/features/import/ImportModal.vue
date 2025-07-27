<!--
  - coding=utf-8
  - Copyright 2021-present, the Recognai S.L. team.
  -
  - Licensed under the Apache License, Version 2.0 (the "License");
  - you may not use this file except in compliance with the License.
  - You may obtain a copy of the License at
  -
  -     http://www.apache.org/licenses/LICENSE-2.0
  -
  - Unless required by applicable law or agreed to in writing, software
  - distributed under the License is distributed on an "AS IS" BASIS,
  - WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  - See the License for the specific language governing permissions and
  - limitations under the License.
  -->

<template>
  <BaseModal
    v-if="isVisible"
    class="import-modal"
    :modal-custom="true"
    @close-modal="$emit('close')"
  >
    <div class="import-modal__container">
      <div class="import-modal__header">
        <h2 class="import-modal__title">Import Documents</h2>
        <BaseButton
          class="import-modal__close-button"
          @click="$emit('close')"
        >
          <svgicon name="close" width="16" aria-hidden="true"></svgicon>
        </BaseButton>
      </div>

      <div class="import-modal__content">
        <div class="import-modal__placeholder">
          <svgicon
            name="import"
            width="64"
            height="64"
            class="import-modal__placeholder-icon"
            aria-hidden="true"
          />
          <h3>Import Documents Feature</h3>
          <p>This feature is currently under development.</p>
          <p>It will allow you to import your reference library from .bib files and PDF folders.</p>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<script>
import "assets/icons/close";
import "assets/icons/import";

export default {
  name: "ImportModal",
  props: {
    isVisible: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["close"],
};
</script>

<style lang="scss" scoped>
.import-modal {
  &__container {
    width: 90vw;
    max-width: 1200px;
    height: 90vh;
    max-height: 800px;
    background: var(--bg-primary);
    border-radius: $border-radius-m;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $base-space * 3;
    border-bottom: 1px solid var(--bg-opacity-10);
    background: var(--bg-secondary);
  }

  &__title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--fg-primary);
  }

  &__close-button.button {
    padding: $base-space;
    background: transparent;
    border: none;
    color: var(--fg-secondary);

    &:hover {
      background: var(--bg-opacity-10);
      color: var(--fg-primary);
    }
  }

  &__content {
    flex: 1;
    padding: $base-space * 4;
    overflow: auto;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__placeholder {
    text-align: center;
    max-width: 400px;

    h3 {
      margin: $base-space * 2 0 $base-space 0;
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--fg-primary);
    }

    p {
      margin: $base-space 0;
      color: var(--fg-secondary);
      line-height: 1.5;
    }
  }

  &__placeholder-icon {
    color: var(--fg-tertiary);
    opacity: 0.6;
  }
}
</style>