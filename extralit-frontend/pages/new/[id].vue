<template></template>

<script setup lang="ts">
definePageMeta({
  middleware(to) {
    if (to.params.id) {
      return navigateTo(encodeURIComponent(to.params.id as string));
    } else {
      return navigateTo("/");
    }
  },
});
</script>
