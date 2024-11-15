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
      console.log("ImportDocuments button clicked");
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
