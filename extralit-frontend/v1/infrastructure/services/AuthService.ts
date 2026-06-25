import { shallowRef, type Ref } from "vue";
import type { IAuthService } from "~/v1/domain/services/IAuthService";

// Replaces @nuxtjs/auth-next. Only ever used as a token store + loggedIn flag
// (all auth-next endpoints were disabled; OIDC lives in extralit-server). The
// token is held in a Nuxt `useCookie` ref injected at plugin time, which keeps
// this class unit-testable with a plain ref.
export class AuthService implements IAuthService {
  // Backed by a shallowRef so `user` is reactive: auth-next exposed a reactive
  // $auth.user, and useUser()/useRole() wrap it in computeds that must update
  // when the user is (re)loaded. The user object is replaced wholesale, so
  // reference-level (shallow) reactivity is sufficient.
  private readonly _user = shallowRef<Record<string, unknown> | null>(null);

  constructor(private readonly tokenRef: Ref<string | null | undefined>) {}

  get token(): string | null {
    return this.tokenRef.value ?? null;
  }

  get loggedIn(): boolean {
    return !!this.tokenRef.value;
  }

  get user(): Record<string, unknown> | null {
    return this._user.value;
  }

  setUser(user: unknown): void {
    this._user.value = (user as Record<string, unknown>) ?? null;
  }

  async setUserToken(token: string): Promise<void> {
    this.tokenRef.value = token;
  }

  async logout(): Promise<void> {
    this.tokenRef.value = null;
    this._user.value = null;
  }
}
