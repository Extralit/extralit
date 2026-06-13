import { defineNuxtPlugin, useCookie } from "#app";
import { AuthService } from "~/v1/infrastructure/services/AuthService";

// Provides $auth (token store + loggedIn flag), replacing @nuxtjs/auth-next.
// Ordered first (1.) so 2.axios and 3.di can read it.
export default defineNuxtPlugin((nuxtApp) => {
  const token = useCookie<string | null>("auth_token", { sameSite: "lax" });
  nuxtApp.provide("auth", new AuthService(token));
});
