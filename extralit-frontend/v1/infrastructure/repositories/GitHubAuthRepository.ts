import { type NuxtAxiosInstance } from "@nuxtjs/axios";

interface AuthStatusResponse {
  authenticated: boolean;
  username: string;
}

interface DeviceFlowResponse {
  device_code: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
}

interface PollTokenResponse {
  status: "pending" | "authorized" | "error";
  message?: string;
}

export class GitHubAuthRepository {
  // Take the standard authenticated Axios instance directly
  constructor(private readonly axios: NuxtAxiosInstance) { }

  async getStatus(): Promise<AuthStatusResponse> {
    const { data } = await this.axios.get<AuthStatusResponse>(
      "v1/auth/github/status"
    );
    return data;
  }

  async initiateLogin(): Promise<DeviceFlowResponse> {
    const { data } = await this.axios.post<DeviceFlowResponse>(
      "v1/auth/github/login"
    );
    return data;
  }

  async pollToken(deviceCode: string): Promise<PollTokenResponse> {
    const { data } = await this.axios.post<PollTokenResponse>(
      "v1/auth/github/poll",
      { device_code: deviceCode }
    );
    return data;
  }
}