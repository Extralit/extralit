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
  <transition name="show-panel" appear>
    <aside class="sidebar" :class="layoutClass">
      <div class="sidebar__content">
        <base-button
          @click.prevent="closePanel"
          :class="{ 'zoom-out': animated, '--document-panel': layoutClass === '--document-panel' }"
          @animationend="animated = false"
          class="sidebar__close-button"
        >
          <svgicon name="chevron-right" width="12" height="12"></svgicon>
        </base-button>
        <transition name="fade" appear duration="500" mode="out-in">
          <slot></slot>
        </transition>
      </div>
      <div class="sidebar__edge"></div>
    </aside>
  </transition>
</template>

<script>
import "assets/icons/chevron-right";
import interact from 'interactjs'

export default {
  props: {
    currentPanel: {
      type: String,
      required: false,
    },
  },
  data: () => {
    return {
      animated: false,
    };
  },
  methods: {
    closePanel() {
      this.$emit("close-panel");
      this.animated = true;
    },
    getPanelWidth() {
      let panelWidth = parseInt(getComputedStyle(this.$el).width);
      // if (this.currentPanel != 'document') {
      //   const sidebarPanelWidth = 70; // Replace with your actual value of $sidebarPanelWidth
      //   panelWidth += sidebarPanelWidth;
      // }
      return panelWidth + 'px';
    },
  },
  computed: {
    layoutClass() {
      return this.currentPanel === 'document' ? "--document-panel" : null;
    },
  },
  mounted() {
    // Set the initial sidebar width
    this.$el.style.width = this.getPanelWidth();
    document.documentElement.style.setProperty('--sidebar-width', this.$el.style.width);

    interact(this.$el)
      .resizable({
        edges: { left: true, right: false, bottom: false, top: false },
        modifiers: [
          interact.modifiers.restrictSize({
            min: { width: 200, height: 0 },
          }),
        ],
      })
      .on('resizemove', event => {
        let target = event.target;
        target.style.width = event.rect.width + 'px';
        document.documentElement.style.setProperty('--sidebar-width', target.style.width);
      });
  },
};
</script>

<style lang="scss" scoped>
.sidebar {
  $this: &;
  width: $sidebarPanelWidth;
  position: relative;
  top: 0;
  right: 0;
  background: palette(grey, 700);
  padding: 1em 1.5em 0 1.5em;
  border-left: 1px solid palette(grey, 600);
  overflow: visible;
  pointer-events: all;
  &.--document-panel {
    width: calc($sidebarWidth + $sidebarDocumentAdditionalWidth);
    padding: 0 0 0 0;
  }
  &:hover {
    #{$this}__close-button:not(.zoom-out) {
      opacity: 1;
      transform: scale(1);
      transition: transform 0.15s ease-in-out;
    }
  }
  &__close-button {
    position: absolute;
    left: -2.5em;
    &.--document-panel {
      left: -0.65em;
      top: 1em;
    }
    top: 1px;
    display: flex;
    overflow: hidden;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    padding: 0;
    background: palette(grey, 600);
    opacity: 0;
    outline: 0;
    border-radius: $border-radius-s;
    transform: scale(0);
    z-index: 1;
    &.zoom-out {
      opacity: 1;
      animation: zoom-out 0.3s ease-out forwards;
    }
    .svg-icon {
      color: palette(blue, 300);
    }
  }
  &__content {
    display: block;
    position: relative;
    color: $black-54;
  }
  &__content {
    @include font-size(13px);
    &:first-child {
      padding-top: 0;
    }
  }

  &__edge {
    position: absolute;
    top: 50px;
    left: 0;
    bottom: 0;
    width: 5px; 
    background: transparent;
    z-index: 1;
    transition: background 0.3s ease;

    &::before {
      content: "";
      position: absolute;
      top: 0;
      left: -30px; // Adjust this to change the hover area width
      bottom: 0;
      width: 60px;
      background: transparent;
      z-index: -1;
    }

    &:hover {
      background: $primary-lighten-color;
    }
  }
}

.show-panel-enter-active {
  animation: slide 0.4s ease-out;
}
.show-panel-leave-active {
  animation: slide 0.4s reverse ease-in;
}
.show-panel-enter-active {
  .sidebar__content {
    opacity: 0;
    animation: fade 0.2s ease-out 0.3s;
  }
}
.show-panel-leave-active {
  .sidebar__content {
    opacity: 0;
    animation: fade 0.1s reverse ease-in;
  }
}
@keyframes slide {
  0% {
    right: -$sidebarPanelWidth + 1px;
  }
  100% {
    right: 0;
  }
}
@keyframes fade {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}
@keyframes zoom-out {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(0);
  }
  100% {
    transform: scale(0);
  }
}
</style>
