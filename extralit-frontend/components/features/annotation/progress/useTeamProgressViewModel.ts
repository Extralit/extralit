import { onBeforeMount } from "vue";
import { useEvents, UpdateTeamProgressEventHandler } from "~/v1/infrastructure/events";
import { useTeamProgress } from "~/v1/infrastructure/storage/TeamProgressStorage";

export const useTeamProgressViewModel = () => {
  const { state: progress } = useTeamProgress();

  onBeforeMount(() => {
    useEvents(UpdateTeamProgressEventHandler);
  });

  return {
    progress,
  };
};
