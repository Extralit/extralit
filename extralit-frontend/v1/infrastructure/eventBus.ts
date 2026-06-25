import mitt from "mitt";

// Replaces the Vue 2 `$root`/`$nuxt` global event bus (removed in Vue 3).
// Single shared instance: annotation components emit/listen for record
// criteria/page/metadata changes across the tree.
export const eventBus = mitt();
