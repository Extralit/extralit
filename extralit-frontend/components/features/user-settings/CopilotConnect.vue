<template>
  <div class="copilot-connect">
    <!-- Connected State -->
    <div v-if="isAuthenticated" class="copilot-connect__status copilot-connect__status--connected">
      <span class="copilot-connect__icon">✓</span>
      <span class="copilot-connect__label">GitHub Copilot Connected</span>
    </div>

    <!-- Pending State -->
    <div v-else-if="isPending" class="copilot-connect__status copilot-connect__status--pending">
      <div class="copilot-connect__instructions">
        <p class="copilot-connect__text">
          Go to
          <a
            :href="verificationUri"
            target="_blank"
            rel="noopener noreferrer"
            class="copilot-connect__link"
          >{{ verificationUri }}</a>
          and enter the code:
        </p>
        <div class="copilot-connect__code-box">
          <code class="copilot-connect__code">{{ userCode }}</code>
        </div>
      </div>
      <div class="copilot-connect__spinner-row">
        <span class="copilot-connect__spinner" />
        <span class="copilot-connect__waiting-text">Waiting for authorization…</span>
      </div>
    </div>

    <!-- Disconnected State -->
    <div v-else class="copilot-connect__status copilot-connect__status--disconnected">
      <button
        class="copilot-connect__button"
        @click="connectCopilot"
      >
        Connect Copilot
      </button>
    </div>
  </div>
</template>

<script>
import { useCopilotConnectViewModel } from "./useCopilotConnectViewModel";

export default {
  setup() {
    return useCopilotConnectViewModel();
  },
};
</script>

<style lang="scss" scoped>
.copilot-connect {
  padding: $base-space * 2 0;

  &__status {
    display: flex;
    align-items: center;
    gap: $base-space * 2;
    flex-wrap: wrap;

    &--connected {
      color: var(--fg-primary);
    }

    &--pending {
      flex-direction: column;
      align-items: flex-start;
      gap: $base-space * 3;
    }

    &--disconnected {
      // defaults are fine
    }
  }

  &__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background-color: #2da44e;
    color: #fff;
    font-size: 14px;
    font-weight: bold;
    flex-shrink: 0;
  }

  &__label {
    font-weight: 500;
    color: var(--fg-primary);
  }

  &__instructions {
    display: flex;
    flex-direction: column;
    gap: $base-space;
  }

  &__text {
    margin: 0;
    color: var(--fg-secondary);
  }

  &__link {
    color: var(--color-brand);
    text-decoration: underline;

    &:hover {
      text-decoration: none;
    }
  }

  &__code-box {
    display: inline-flex;
    padding: $base-space $base-space * 2;
    background: var(--bg-opacity-4);
    border: 1px solid var(--bg-opacity-10);
    border-radius: 6px;
  }

  &__code {
    font-family: monospace;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 3px;
    color: var(--fg-primary);
  }

  &__spinner-row {
    display: flex;
    align-items: center;
    gap: $base-space;
  }

  &__spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid var(--bg-opacity-10);
    border-top-color: var(--color-brand);
    border-radius: 50%;
    animation: copilot-spin 0.8s linear infinite;
  }

  &__waiting-text {
    color: var(--fg-secondary);
    font-size: 13px;
  }

  &__button {
    display: inline-flex;
    align-items: center;
    padding: $base-space $base-space * 3;
    background-color: var(--color-brand);
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s ease;

    &:hover {
      opacity: 0.9;
    }
  }
}

@keyframes copilot-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
