import { ref, onMounted } from "vue";
import { useRunningEnvironment } from "@/v1/infrastructure/services/useRunningEnvironment";
import { useRole } from "@/v1/infrastructure/services";

export const usePersistentStorageViewModel = () => {
  const showBanner = ref(false);
  const { hasPersistentStorageWarning } = useRunningEnvironment();
  const { isAdminOrOwnerRole } = useRole();

  onMounted(async () => {
    try {
      showBanner.value = await hasPersistentStorageWarning();
    } catch {
      /* best-effort: keep banner hidden if the check fails */
    }
  });

  return {
    showBanner,
    isAdminOrOwnerRole,
  };
};
