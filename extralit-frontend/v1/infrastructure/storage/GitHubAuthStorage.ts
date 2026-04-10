import { useStoreFor } from "@/v1/store/create";

class GitHubAuthState {
  constructor(
    public readonly isAuthenticated: boolean = false,
    public readonly isPending: boolean = false,
    public readonly userCode: string | null = null,
    public readonly verificationUri: string | null = null,
    public readonly errorMessage: string | null = null
  ) {}
}

const useStoreForGitHubAuth = useStoreFor<GitHubAuthState, {}>(GitHubAuthState);

export const useGitHubAuth = () => useStoreForGitHubAuth();
