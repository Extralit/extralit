import { onBeforeUnmount, onMounted } from "vue";

export const useFocusTab = (
  onFocus: () => void,
  onBlur: () => void = () => {
    /* no-op */
  }
) => {
  if (!onFocus) throw new Error("onFocus is mandatory");

  const onFocusCallback = () => onFocus();

  onMounted(() => {
    window.addEventListener("focus", onFocusCallback);
    window.addEventListener("blur", onBlur);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("focus", onFocusCallback);
    window.removeEventListener("blur", onBlur);
  });
};
