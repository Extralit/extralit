import { GitHubAuthRepository } from "@/v1/infrastructure/repositories/GitHubAuthRepository";

export class GitHubAuthUseCase {
  private pollingTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly repository: GitHubAuthRepository,
    private readonly store: any
  ) {}

  async checkStatus(): Promise<void> {
    try {
      const { authenticated } = await this.repository.getStatus();
      const current = this.store.get();
      this.store.save({
        ...current,
        isAuthenticated: authenticated,
        isPending: false,
        userCode: null,
        verificationUri: null,
        deviceCode: null,
      });
    } catch {
      // If the check fails, leave current state unchanged
    }
  }

  async initiateLogin(): Promise<void> {
    const response = await this.repository.initiateLogin();

    const current = this.store.get();
    this.store.save({
      ...current,
      isPending: true,
      userCode: response.user_code,
      verificationUri: response.verification_uri,
      deviceCode: response.device_code,
      isAuthenticated: false,
    });

    this.startPolling(response.device_code, response.interval);
  }

  clearPolling(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
  }

  private startPolling(deviceCode: string, intervalSeconds: number): void {
    this.clearPolling();

    // Use at least 5 seconds between polls to avoid rate limiting
    const pollInterval = Math.max(intervalSeconds, 5) * 1000;

    this.pollingTimer = setInterval(async () => {
      try {
        const { status } = await this.repository.pollToken(deviceCode);

        if (status === "authorized") {
          this.clearPolling();
          const current = this.store.get();
          this.store.save({
            ...current,
            isAuthenticated: true,
            isPending: false,
            userCode: null,
            verificationUri: null,
            deviceCode: null,
          });
        } else if (status === "error") {
          this.clearPolling();
          const current = this.store.get();
          this.store.save({
            ...current,
            isAuthenticated: false,
            isPending: false,
            userCode: null,
            verificationUri: null,
            deviceCode: null,
          });
        }
        // "pending" — keep polling
      } catch {
        this.clearPolling();
        const current = this.store.get();
        this.store.save({
          ...current,
          isAuthenticated: false,
          isPending: false,
          userCode: null,
          verificationUri: null,
          deviceCode: null,
        });
      }
    }, pollInterval);
  }
}
