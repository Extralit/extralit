import { useClipboard } from "~/v1/infrastructure/services/useClipboard";

export default (_, inject) => {
  const { copy } = useClipboard();

  inject("copyToClipboard", copy);
};
