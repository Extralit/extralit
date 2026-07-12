import { onBeforeMount, ref } from "vue";
import { useResolve } from "ts-injecty";
import { GetSchemaSettingsUseCase, type SchemaSettings } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { RebuildSchemaIndexUseCase } from "~/v2/domain/usecases/rebuild-schema-index-use-case";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";
import { useTranslate } from "~/v1/infrastructure/services/useTranslate";

export const useSchemaSettingsViewModel = (schemaId: string) => {
  const getSettingsUseCase = useResolve(GetSchemaSettingsUseCase);
  const rebuildIndexUseCase = useResolve(RebuildSchemaIndexUseCase);
  const notifications = useNotifications();
  const { t } = useTranslate();

  const settings = ref<SchemaSettings | null>(null);
  const isLoading = ref(false);
  const isRebuilding = ref(false);

  const load = async () => {
    isLoading.value = true;
    try {
      settings.value = await getSettingsUseCase.execute(schemaId);
    } finally {
      isLoading.value = false;
    }
  };

  const rebuildIndex = async () => {
    isRebuilding.value = true;
    try {
      const indexed = await rebuildIndexUseCase.execute(schemaId);
      notifications.notify({ message: t("schemas.rebuildIndexDone", { count: indexed }), type: "success" });
    } finally {
      isRebuilding.value = false;
    }
  };

  onBeforeMount(load);

  return { settings, isLoading, isRebuilding, load, rebuildIndex };
};
