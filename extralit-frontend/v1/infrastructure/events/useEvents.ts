import { DomainEvent, Handler } from "@codescouts/events";
import { useResolve, Class } from "ts-injecty";
import { onMounted, onUnmounted, ref } from "vue";

export const useEvents = (...handlers: Class<Handler<DomainEvent>>[]) => {
  const resolved = ref([]);

  onMounted(() => {
    resolved.value = handlers.map((handler) => useResolve(handler));
  });

  onUnmounted(() => {
    resolved.value.forEach((handler) => handler.dispose());
  });
};
