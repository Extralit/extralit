import { onBeforeMount, ref } from "vue";
import { useResolve } from "ts-injecty";
import { GetSchemaSettingsUseCase, type SchemaSettings } from "~/v2/domain/usecases/get-schema-settings-use-case";

export const useSchemaSettingsViewModel = (schemaId: string) => {
  const getSettingsUseCase = useResolve(GetSchemaSettingsUseCase);

  const settings = ref<SchemaSettings | null>(null);
  const isLoading = ref(false);
  const loadFailed = ref(false);

  const load = async () => {
    isLoading.value = true;
    loadFailed.value = false;
    try {
      settings.value = await getSettingsUseCase.execute(schemaId);
    } catch {
      loadFailed.value = true; // AxiosErrorHandler already notified
    } finally {
      isLoading.value = false;
    }
  };

  onBeforeMount(load);

  return { settings, isLoading, loadFailed, load };
};
