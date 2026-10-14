import Container, { register, Class } from "ts-injecty";

export const useResolveMock = <T>(ctor: Class<T>, mocked: object) => {
  Container.register([register(ctor.name).withImplementation(mocked).build()]);
};
