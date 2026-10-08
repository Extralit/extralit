export interface IAuthService {
  get loggedIn(): boolean;
  get user(): Record<string, unknown> | null;
  logout(...args: unknown[]): Promise<void>;
  setUserToken(token: string): Promise<void>;
  setUser(user: unknown): void;
}
