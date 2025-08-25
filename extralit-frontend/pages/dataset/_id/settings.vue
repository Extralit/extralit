<template>
  <div>
    <p>This page has been moved. Dataset settings are now available as a modal. Redirecting...</p>
  </div>
</template>

<script>
export default {
  name: "SettingPageRedirect",
  mounted() {
    // Redirect to the home page
    this.$router.push("/");
  },
};
</script>
