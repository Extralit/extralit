import { shallowMount, flushPromises } from "@vue/test-utils";
import SignIn from "./sign-in.vue";

// @vue/test-utils v2: top-level stubs/mocks move under `global`.
const stubs = {
  BaseLoading: true,
  "brand-logo": true,
  "geometric-shape-a": true,
  "base-button": true,
  OAuthLogin: true,
  LoginInput: true,
  AuthenticationLayout: { template: "<div><slot /></div>" },
};

const validAuthToken = btoa("USERNAME:PASSWORD");

// The component's setup() returns useSignInViewModel(), which must expose `login`.
const loginMock = vi.fn();

vi.mock("./useSignInViewModel", () => ({
  useSignInViewModel: () => ({ login: loginMock }),
}));

const mountLoginPage = ({ auth } = {}) => {
  return shallowMount(SignIn, {
    global: {
      stubs,
      mocks: {
        $config: {},
        $route: {
          query: {
            auth,
          },
        },
      },
    },
  });
};

describe("Login page should", () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it("still in the same page if the auth token is not valid", () => {
    const loginUserSpy = vi.spyOn(SignIn.methods, "loginUser");

    mountLoginPage({ auth: "INVALID" });

    expect(loginUserSpy).toHaveBeenCalledTimes(0);
  });

  it("still in the same page if the auth token query params is empty", () => {
    const loginUserSpy = vi.spyOn(SignIn.methods, "loginUser");

    mountLoginPage();

    expect(loginUserSpy).toHaveBeenCalledTimes(0);
  });

  it("try to login user when the auth token is valid", async () => {
    const loginUserSpy = vi.spyOn(SignIn.methods, "loginUser");

    mountLoginPage({ auth: validAuthToken });
    await flushPromises();

    expect(loginUserSpy).toHaveBeenCalledTimes(1);
  });

  it("the auth token is valid when the object has the username and password", async () => {
    const wrapper = mountLoginPage({ auth: validAuthToken });
    await flushPromises();

    expect(wrapper.vm.hasAuthToken).toBeTruthy();
  });

  it("the auth token is not valid when the object has username but no password", () => {
    const auth = btoa("USERNAME:");

    const wrapper = mountLoginPage({ auth });

    expect(wrapper.vm.hasAuthToken).toBeFalsy();
  });

  it("the auth token is not valid when the object has no username but password", () => {
    const auth = btoa(":PASSWORD");

    const wrapper = mountLoginPage({ auth });

    expect(wrapper.vm.hasAuthToken).toBeFalsy();
  });

  it("the auth token is not valid when the object has no username and no password", () => {
    const auth = btoa(":");

    const wrapper = mountLoginPage({ auth });

    expect(wrapper.vm.hasAuthToken).toBeFalsy();
  });

  it("the auth token is not valid when the object other object structure", () => {
    const auth = btoa("FOO");

    const wrapper = mountLoginPage({ auth });

    expect(wrapper.vm.hasAuthToken).toBeFalsy();
  });

  it("show the loading logo when the token is valid", async () => {
    const wrapper = mountLoginPage({ auth: validAuthToken });
    await flushPromises();

    const loadingLogo = wrapper.findComponent({
      name: "BaseLoading",
    });
    expect(loadingLogo.exists()).toBeTruthy();
  });

  it("no show the loading logo when the token is not valid", () => {
    const auth = "";

    const wrapper = mountLoginPage({ auth });

    const loadingLogo = wrapper.findComponent({
      name: "BaseLoading",
    });
    expect(loadingLogo.exists()).toBeFalsy();
  });
});
