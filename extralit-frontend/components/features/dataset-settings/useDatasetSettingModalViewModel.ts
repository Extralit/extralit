import { computed, onBeforeMount, onBeforeUnmount, ref, watch } from "vue-demi";
import { useResolve } from "ts-injecty";
import { GetDatasetSettingsUseCase } from "~/v1/domain/usecases/dataset-setting/get-dataset-settings-use-case";
import { useDatasetSetting } from "~/v1/infrastructure/storage/DatasetSettingStorage";
import { useBeforeUnload, useRole, useRoutes, useTranslate } from "@/v1/infrastructure/services";
import { DatasetSetting } from "~/v1/domain/entities/dataset/DatasetSetting";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";
import { DATASET_API_ERRORS } from "@/v1/infrastructure/repositories/DatasetRepository";

interface Tab {
  id: "general" | "fields" | "questions" | "metadata" | "vector" | "danger-zone";
  name: string;
  component: string;
}

export const useDatasetSettingModalViewModel = (datasetId: string) => {
  const notification = useNotifications();
  const routes = useRoutes();
  const beforeUnload = useBeforeUnload();
  const { t } = useTranslate();

  const { isAdminOrOwnerRole } = useRole();
  const { state: datasetSetting } = useDatasetSetting();

  const getDatasetSetting = useResolve(GetDatasetSettingsUseCase);

  const tabs = ref<Tab[]>([]);
  const isLoadingDataset = ref(false);

  const handleError = (response: string) => {
    let message = "";
    switch (response) {
      case DATASET_API_ERRORS.ERROR_FETCHING_DATASET_INFO:
        message = `Can't get dataset info for dataset_id: ${datasetId}`;
        break;
      case DATASET_API_ERRORS.ERROR_FETCHING_WORKSPACE_INFO:
        message = `Can't get workspace info for dataset_id: ${datasetId}`;
        break;
      default:
        message = "There was an error on fetching dataset info and workspace info. Please try again";
    }

    notification.notify({
      message,
      type: "danger",
    });
  };

  const createRootBreadCrumbs = (dataset?: any) => {
    if (!dataset) return [];
    
    return [
      {
        link: { name: "index" },
        name: t("home.title"),
      },
      {
        link: routes.getDatasetLink(dataset),
        name: dataset.name,
      },
    ];
  };

  const configureTabs = (datasetSettings: DatasetSetting) => {
    tabs.value = []; // Reset tabs
    
    tabs.value.push({
      id: "general",
      name: t("general"),
      component: "SettingsInfo",
    });
    tabs.value.push({
      id: "fields",
      name: t("fields"),
      component: "SettingsFields",
    });
    tabs.value.push({
      id: "questions",
      name: t("questions"),
      component: "SettingsQuestions",
    });

    if (datasetSettings.hasMetadataProperties) {
      tabs.value.push({
        id: "metadata",
        name: t("metadata"),
        component: "SettingsMetadata",
      });
    }

    if (datasetSettings.hasVectors) {
      tabs.value.push({
        id: "vector",
        name: t("vectors"),
        component: "SettingsVectors",
      });
    }

    tabs.value.push({
      id: "danger-zone",
      name: t("dangerZone"),
      component: "SettingsDangerZone",
    });
  };

  const loadDatasetSetting = async () => {
    try {
      isLoadingDataset.value = true;

      const datasetSettings = await getDatasetSetting.execute(datasetId);
      configureTabs(datasetSettings);
    } catch (error) {
      handleError(error.response);
    } finally {
      isLoadingDataset.value = false;
    }
  };

  const breadcrumbs = computed(() => {
    return [
      ...createRootBreadCrumbs(datasetSetting.dataset),
      {
        link: {},
        name: t("breadcrumbs.datasetSettings"),
      },
    ];
  });

  const goToDataset = () => {
    routes.goToFeedbackTaskAnnotationPage(datasetId);
  };

  const goToTab = (id: Tab["id"]) => {
    document.getElementById(id)?.click();
  };

  const goToTabWithModification = () => {
    if (datasetSetting.isDatasetModified) return goToTab("general");
    if (datasetSetting.isFieldsModified) return goToTab("fields");
    if (datasetSetting.isQuestionsModified) return goToTab("questions");
    if (datasetSetting.isMetadataPropertiesModified) return goToTab("metadata");
    if (datasetSetting.isVectorsModified) return goToTab("vector");
  };

  const goToOutside = (next) => {
    if (datasetSetting.isModified) {
      return notification.notify({
        message: t("changes_no_submit"),
        buttonText: t("button.ignore_and_continue"),
        permanent: true,
        type: "warning",
        onClick() {
          next();
        },
        onClose() {
          goToTabWithModification();
        },
      });
    }

    next();
  };

  onBeforeMount(() => {
    if (datasetId) {
      loadDatasetSetting();
    }
  });

  onBeforeUnmount(() => {
    beforeUnload.destroy();
  });

  watch(
    () => datasetSetting.isModified,
    (isModified) => {
      if (isModified) return beforeUnload.confirm();

      beforeUnload.destroy();
    }
  );

  const onTabChanged = async (_tabId: Tab["id"]) => {
    // For modal, we don't need to update URL query params
    // Just keep this for compatibility if needed
  };

  const onTabLoaded = () => {
    // For modal, we can skip URL-based tab selection
    // Just keep this for compatibility if needed
  };

  return {
    isLoadingDataset,
    breadcrumbs,
    tabs,
    isAdminOrOwnerRole,
    datasetId,
    datasetSetting,
    goToOutside,
    goToDataset,
    onTabChanged,
    onTabLoaded,
  };
};