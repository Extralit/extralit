import { type NuxtAxiosInstance } from "@nuxtjs/axios";

type PublicAxiosConfig = {
  enableErrors: boolean;
  removeAuthorizationHeader?: boolean;
};

export interface PublicNuxtAxiosInstance extends NuxtAxiosInstance {
  makePublic: (config?: PublicAxiosConfig) => NuxtAxiosInstance;
}

export const useAxiosExtension = (axiosInstanceFn: () => NuxtAxiosInstance) => {
  const makePublic = (axios: NuxtAxiosInstance, config: PublicAxiosConfig) => {
    const publicAxios = axios.create({
      withCredentials: false,
    });

    if (config.enableErrors) {
      publicAxios.interceptors.response = axios.interceptors.response;
    }

    // Remove Authorization header for get requests if specified
    if (config.removeAuthorizationHeader) {
      const originalGet = publicAxios.get;
      publicAxios.get = function(...args) {
        const config = args[1] || {};
        if (!config.headers) {
          config.headers = {};
        }
        config.headers['Authorization'] = undefined;
        args[1] = config;
        return originalGet.apply(this, args);
      };
    }

    return publicAxios;
  };

  const create = () => {
    const axios = axiosInstanceFn();

    return {
      ...axios,
      makePublic: (
        config: PublicAxiosConfig = {
          enableErrors: true,
          removeAuthorizationHeader: false
        }
      ) => makePublic(axios, config),
    } as PublicNuxtAxiosInstance;
  };

  return create;
};
