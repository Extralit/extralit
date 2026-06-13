import type { IAuthService } from "~/v1/domain/services/IAuthService";

// The notification helper provided as $notification by plugins/extensions.ts
// (provide.notification -> $notification). Mirrors useNotifications()'s shape.
type NotificationService = {
  notify: (params: {
    message: string;
    type?: "success" | "info" | "warning" | "danger";
    permanent?: boolean;
    buttonText?: string;
    onClick?: () => void;
    onClose?: () => void;
  }) => ReturnType<typeof setTimeout>;
  clear: () => void;
};

// Augment the Nuxt app and Vue component instance with the $auth service
// provided by plugins/1.auth.ts (replaces @nuxtjs/auth-next typings).
declare module "#app" {
  interface NuxtApp {
    $auth: IAuthService;
  }
}

declare module "vue" {
  interface ComponentCustomProperties {
    $auth: IAuthService;
    $notification: NotificationService;
  }
}

export {};
