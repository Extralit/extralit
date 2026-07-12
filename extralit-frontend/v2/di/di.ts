import type { AxiosInstance } from "axios";
import Container, { register } from "ts-injecty";

import { useAxiosExtension } from "@/v1/infrastructure/services/useAxiosExtension";

import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";

type NuxtAppLike = {
  $axios: AxiosInstance;
  $i18n?: { t: (key: string) => unknown };
};

// Same global ts-injecty container as v1 (registrations keyed by class name — v2 names
// are disjoint from v1's by the Global Constraints rule). Called after v1's loader.
export const loadV2DependencyContainer = (nuxtApp: NuxtAppLike) => {
  const t = (key: string) => String(nuxtApp.$i18n?.t(key) ?? key);
  const useAxios = useAxiosExtension(nuxtApp.$axios, t);

  const dependencies = [
    register(SchemaRepository).withDependency(useAxios).build(),
    register(GetSchemasUseCase).withDependencies(SchemaRepository, useSchemas).build(),
    register(GetSchemaSettingsUseCase).withDependency(SchemaRepository).build(),
  ];

  Container.register(dependencies);
};
