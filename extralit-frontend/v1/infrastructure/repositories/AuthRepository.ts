import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import { PublicNuxtAxiosInstance } from "../services/useAxiosExtension";
import { IAuthRepository } from "~/v1/domain/services/IAuthRepository";

interface TokenResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
}

export class AuthRepository implements IAuthRepository {
  private readonly axios: NuxtAxiosInstance;
  private refreshToken: string | null = null;

  constructor(axios: PublicNuxtAxiosInstance) {
    this.axios = axios.makePublic();
  }

  async login(username: string, password: string) {
    const url = "/v1/token";
    const request = this.encodedLoginData(username, password);

    const { data } = await this.axios.post<TokenResponse>(url, request, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    // Store refresh token if provided
    if (data.refresh_token) {
      this.refreshToken = data.refresh_token;
      // Store in localStorage for persistence across sessions
      if (process.client) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
    }

    return data.access_token;
  }

  async refreshAccessToken(): Promise<string | null> {
    if (!this.refreshToken) {
      // Try to load from localStorage if not in memory
      if (process.client) {
        this.refreshToken = localStorage.getItem('refresh_token');
      }
      if (!this.refreshToken) {
        return null;
      }
    }

    try {
      const { data } = await this.axios.post<TokenResponse>("/v1/token/refresh", {
        refresh_token: this.refreshToken,
      });

      return data.access_token;
    } catch (error) {
      // If refresh fails, clear stored refresh token
      this.refreshToken = null;
      if (process.client) {
        localStorage.removeItem('refresh_token');
      }
      throw error;
    }
  }

  logout() {
    this.refreshToken = null;
    if (process.client) {
      localStorage.removeItem('refresh_token');
    }
  }

  private encodedLoginData(username: string, password: string) {
    return `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
  }
}
