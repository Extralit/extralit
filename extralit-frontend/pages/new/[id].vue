<template></template>

<script setup lang="ts">
definePageMeta({
  middleware(to) {
    if (to.params.id) {
      return navigateTo(`/new/${encodeURIComponent(to.params.id as string)}`);
    } else {
      return navigateTo("/");
    }
  },
});
</script>
