import { computed, onBeforeMount, ref, watch } from "vue";
import { useResolve } from "ts-injecty";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { Schema } from "~/v2/domain/entities/schema/Schema";
// Documented v1 exception: workspace selection survives Phase 6 (see plan Global Constraints).
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

export const useSchemasViewModel = () => {
  const getSchemasUseCase = useResolve(GetSchemasUseCase);
  const workspacesStore = useWorkspaces();

  const schemas = ref<Schema[]>([]);
  const isLoading = ref(false);
  const loadFailed = ref(false);

  const selectedWorkspace = computed(() => workspacesStore.get().selectedWorkspace);

  const loadSchemas = async () => {
    if (!selectedWorkspace.value) return;
    isLoading.value = true;
    loadFailed.value = false;
    try {
      schemas.value = await getSchemasUseCase.execute(selectedWorkspace.value.id);
    } catch {
      loadFailed.value = true; // AxiosErrorHandler already notified
    } finally {
      isLoading.value = false;
    }
  };

  onBeforeMount(loadSchemas);
  watch(selectedWorkspace, loadSchemas);

  return { schemas, isLoading, loadFailed, selectedWorkspace, loadSchemas };
};
