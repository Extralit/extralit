import axios, { type AxiosInstance } from "axios";
import { loadCache } from "../repositories/AxiosCache";
import { loadErrorHandler } from "../repositories/AxiosErrorHandler";

type PublicAxiosConfig = {
  enableErrors: boolean;
};

export interface PublicAxiosInstance extends AxiosInstance {
  makePublic: (config?: PublicAxiosConfig) => AxiosInstance;
}

// Reimplements the old `useAxiosExtension(context)` against a plain axios instance.
// `makePublic()` builds an unauthenticated instance (used by OAuthRepository).
export const useAxiosExtension = (base: AxiosInstance, t: (key: string) => string) => {
  const makePublic = (config: PublicAxiosConfig = { enableErrors: true }) => {
    const pub = axios.create({
      baseURL: base.defaults.baseURL,
      withCredentials: false,
      headers: { Authorization: undefined },
    });

    if (config.enableErrors) loadErrorHandler(pub, t);

    loadCache(pub);

    return pub;
  };

  const create = () => Object.assign(base, { makePublic }) as PublicAxiosInstance;

  return create;
};
