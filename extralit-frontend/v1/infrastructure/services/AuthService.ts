import type { Ref } from "vue";
import type { IAuthService } from "~/v1/domain/services/IAuthService";

// Replaces @nuxtjs/auth-next. Only ever used as a token store + loggedIn flag
// (all auth-next endpoints were disabled; OIDC lives in extralit-server). The
// token is held in a Nuxt `useCookie` ref injected at plugin time, which keeps
// this class unit-testable with a plain ref.
export class AuthService implements IAuthService {
  private _user: Record<string, unknown> | null = null;

  constructor(private readonly tokenRef: Ref<string | null | undefined>) {}

  get token(): string | null {
    return this.tokenRef.value ?? null;
  }

  get loggedIn(): boolean {
    return !!this.tokenRef.value;
  }

  get user(): Record<string, unknown> | null {
    return this._user;
  }

  setUser(user: unknown): void {
    this._user = (user as Record<string, unknown>) ?? null;
  }

  async setUserToken(token: string): Promise<void> {
    this.tokenRef.value = token;
  }

  async logout(): Promise<void> {
    this.tokenRef.value = null;
    this._user = null;
  }
}
