import { useFetch, onBeforeUnmount } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import { computed } from "vue-demi";
import { GitHubAuthUseCase } from "~/v1/domain/usecases/github-auth-use-case";
import { useGitHubAuth } from "~/v1/infrastructure/storage/GitHubAuthStorage";

export const useCopilotConnectViewModel = () => {
  const gitHubAuthUseCase = useResolve(GitHubAuthUseCase);
  const store = useGitHubAuth();

  const isAuthenticated = computed(() => store.state.isAuthenticated);
  const isPending = computed(() => store.state.isPending);
  const userCode = computed(() => store.state.userCode);
  const verificationUri = computed(() => store.state.verificationUri);

  useFetch(async () => {
    await gitHubAuthUseCase.checkStatus();
  });

  const connectCopilot = async () => {
    await gitHubAuthUseCase.initiateLogin();
  };

  onBeforeUnmount(() => {
    gitHubAuthUseCase.clearPolling();
  });

  return {
    isAuthenticated,
    isPending,
    userCode,
    verificationUri,
    connectCopilot,
  };
};
