<template>
  <AuthenticationLayout>
    <BaseLoading v-if="hasAuthToken" />
    <div class="login__form">
      <form class="form" @submit.prevent="onLoginUser">
        <p class="form__title" v-text="$t('login.title')" />
        <LoginInput v-model="username" :name="$t('login.username')" type="text" :autofocus="true" autocomplete="on" />
        <LoginInput v-model="password" :name="$t('login.password')" type="password" autocomplete="on" />
        <base-button type="submit" :disabled="!isButtonEnabled" class="form__button primary full-width">
          <template v-if="isLoading">
            {{ $t("button.logging_in") }}
          </template>
          <template v-else>
            {{ $t("button.login") }}
          </template>
        </base-button>
        <p v-if="error" class="form__error">{{ formattedError }}</p>
      </form>

      <OAuthLogin />
    </div>
  </AuthenticationLayout>
</template>

<script>
import AuthenticationLayout from "@/layouts/AuthenticationLayout";
import { useSignInViewModel } from "./useSignInViewModel";

export default {
  data() {
    return {
      error: undefined,
      username: "",
      password: "",
      hasAuthToken: false,
      isLoading: false,
    };
  },
  components: {
    AuthenticationLayout,
  },
  async created() {
    const rawAuthToken = this.$route.query.auth;

    if (!rawAuthToken) return;

    try {
      const [username, password] = atob(rawAuthToken).split(":");

      if (username && password) {
        this.hasAuthToken = true;
        this.isLoading = true;

        try {
          await this.loginUser({ username, password });
        } catch {
          this.hasAuthToken = false;
        } finally {
          this.isLoading = false;
        }
      }
    } catch {
      /* lint:disable:no-empty */
    }
  },
  computed: {
    formattedError() {
      if (this.error) {
        return this.error.toString().includes("401") ? this.$t("login.error") : this.error;
      }
    },
    isButtonEnabled() {
      return !!this.username && !!this.password && !this.isLoading;
    },
  },
  methods: {
    async loginUser({ username, password }) {
      await this.login(username, password);
    },
    async onLoginUser() {
      this.isLoading = true;
      this.error = undefined;
      try {
        await this.loginUser({
          username: this.username,
          password: this.password,
        });
      } catch (err) {
        this.error = err;
      } finally {
        this.isLoading = false;
      }
    },
  },
  setup() {
    return useSignInViewModel();
  },
};
</script>
