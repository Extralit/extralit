import { useResolve } from "ts-injecty";
import { ref, onMounted } from "vue";
import { GetWorkspacesUseCase } from "~/v1/domain/usecases/get-workspaces-use-case";
import { useUser } from "~/v1/infrastructure/services/useUser";

export const useUserInfoViewModel = () => {
  const isLoadingWorkspaces = ref(false);
  const workspaces = ref<any[]>([]);
  const { user } = useUser();
  const getWorkspacesUseCase = useResolve(GetWorkspacesUseCase);

  onMounted(async () => {
    isLoadingWorkspaces.value = true;
    workspaces.value = await getWorkspacesUseCase.execute();
    isLoadingWorkspaces.value = false;
  });

  return {
    isLoadingWorkspaces,
    workspaces,
    user,
  };
};
