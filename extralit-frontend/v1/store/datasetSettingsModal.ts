import { defineStore } from "pinia";
import { ref } from "vue-demi";

export const useDatasetSettingsModal = defineStore("datasetSettingsModal", () => {
  const isVisible = ref(false);
  const datasetId = ref<string | null>(null);

  const openModal = (id: string) => {
    datasetId.value = id;
    isVisible.value = true;
  };

  const closeModal = () => {
    isVisible.value = false;
    datasetId.value = null;
  };

  return {
    isVisible,
    datasetId,
    openModal,
    closeModal,
  };
});