import { describe, it, expect, beforeEach } from "vitest";
import { AuthService } from "./AuthService";

describe("AuthService", () => {
  let store: Record<string, string | null | undefined>;
  beforeEach(() => {
    store = {};
  });
  const fakeCookie = (k: string) => ({
    get value() {
      return store[k];
    },
    set value(v) {
      store[k] = v;
    },
  });

  it("is logged out with no token", () => {
    const a = new AuthService(fakeCookie("t") as never);
    expect(a.loggedIn).toBe(false);
    expect(a.token).toBeNull();
  });

  it("becomes logged in after setUserToken", async () => {
    const a = new AuthService(fakeCookie("t") as never);
    await a.setUserToken("ABC");
    expect(a.loggedIn).toBe(true);
    expect(a.token).toBe("ABC");
  });

  it("clears token and user on logout", async () => {
    const a = new AuthService(fakeCookie("t") as never);
    await a.setUserToken("ABC");
    a.setUser({ id: 1 });
    expect(a.user).toEqual({ id: 1 });
    await a.logout();
    expect(a.loggedIn).toBe(false);
    expect(a.user).toBeNull();
  });
});
