import { ref } from "vue";
import { useLocalStorage } from "./useLocalStorage";
export const useColorSchema = () => {
  const { get, set } = useLocalStorage();
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";

<<<<<<< HEAD
  const currentTheme = ref(get("theme") || "system");
=======
  const currentTheme = ref(get<string>("theme") || "system");
>>>>>>> v2.6.0

  const setTheme = (theme: string) => {
    currentTheme.value = theme;
    set("theme", theme);

    if (theme !== "system") {
      document.documentElement.setAttribute("data-theme", theme);
    } else {
      document.documentElement.setAttribute("data-theme", systemTheme);
    }
  };

  const initialize = () => {
    setTheme(currentTheme.value);
  };

  return {
    currentTheme,
    setTheme,
    initialize,
  };
};
