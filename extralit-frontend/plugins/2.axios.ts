import axios from "axios";
import { defineNuxtPlugin } from "#app";
import { loadCache } from "~/v1/infrastructure/repositories/AxiosCache";
import { loadErrorHandler } from "~/v1/infrastructure/repositories/AxiosErrorHandler";

// Single HTTP composition root (replaces @nuxtjs/axios). Ordered after 1.auth so the
// request interceptor can read the bearer token from AuthService.
export default defineNuxtPlugin((nuxtApp) => {
  const $i18n = (nuxtApp as { $i18n?: { t: (key: string) => unknown } }).$i18n;
  const t = (key: string) => String($i18n?.t(key) ?? key);

  const instance = axios.create({ baseURL: "/api" });

  instance.interceptors.request.use((config) => {
    const token = (nuxtApp.$auth as { token?: string } | undefined)?.token;
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  loadErrorHandler(instance, t);
  loadCache(instance);

  nuxtApp.provide("axios", instance);
});
