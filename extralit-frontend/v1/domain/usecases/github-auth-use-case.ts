import { GitHubAuthRepository } from "@/v1/infrastructure/repositories/GitHubAuthRepository";
import type { ImplicitStorage } from "@/v1/store/create";

const MIN_POLL_INTERVAL_MS = 5_000;
const MAX_POLL_INTERVAL_MS = 30_000;

interface GitHubAuthState {
  isAuthenticated: boolean;
  isPending: boolean;
  userCode: string | null;
  verificationUri: string | null;
  errorMessage: string | null;
}

type GitHubAuthStore = { state: GitHubAuthState } & ImplicitStorage<GitHubAuthState>;

export class GitHubAuthUseCase {
  private pollingTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;

  constructor(
    private readonly repository: GitHubAuthRepository,
    private readonly store: GitHubAuthStore
  ) {}

  async checkStatus(): Promise<void> {
    try {
      const { authenticated } = await this.repository.getStatus();
      this.saveTerminalState(authenticated);
    } catch (error) {
      console.error("GitHub auth status check failed:", error);
    }
  }

  async initiateLogin(): Promise<void> {
    this.stopped = false;

    const response = await this.repository.initiateLogin();

    this.store.save({
      isAuthenticated: false,
      isPending: true,
      userCode: response.user_code,
      verificationUri: response.verification_uri,
      errorMessage: null,
    });

    this.startPolling(response.interval);
  }

  clearPolling(): void {
    this.stopped = true;
    if (this.pollingTimer) {
      clearTimeout(this.pollingTimer);
      this.pollingTimer = null;
    }
  }

  private saveTerminalState(
    isAuthenticated: boolean,
    errorMessage: string | null = null
  ): void {
    this.clearPolling();
    this.store.save({
      isAuthenticated,
      isPending: false,
      userCode: null,
      verificationUri: null,
      errorMessage,
    });
  }

  private startPolling(intervalSeconds: number): void {
    this.clearPolling();
    this.stopped = false;

    let pollIntervalMs = Math.max(intervalSeconds * 1000, MIN_POLL_INTERVAL_MS);

    const poll = async () => {
      try {
        const { status, message } = await this.repository.pollToken();

        if (this.stopped) return;

        if (status === "authorized") {
          this.saveTerminalState(true);
          return;
        } else if (status === "error") {
          this.saveTerminalState(
            false,
            message || "Authorization failed or expired. Please try again."
          );
          return;
        } else if (status === "slow_down") {
          // RFC 8628: add 5 seconds to the polling interval permanently
          pollIntervalMs = Math.min(pollIntervalMs + MIN_POLL_INTERVAL_MS, MAX_POLL_INTERVAL_MS);
        }

        if (!this.stopped) {
          this.pollingTimer = setTimeout(poll, pollIntervalMs);
        }
      } catch (error) {
        console.error("GitHub auth polling error:", error);
        if (!this.stopped) {
          this.saveTerminalState(false, "Connection error. Please try again.");
        }
      }
    };

    this.pollingTimer = setTimeout(poll, pollIntervalMs);
  }
}
