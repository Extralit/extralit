import type { AxiosInstance } from "axios";
import Container, { register } from "ts-injecty";

import { useAxiosExtension } from "@/v1/infrastructure/services/useAxiosExtension";

import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";
import { ProjectionRepository } from "~/v2/infrastructure/repositories/ProjectionRepository";
import { GetWorkspaceProjectionUseCase } from "~/v2/domain/usecases/get-workspace-projection-use-case";
import { useExtractions } from "~/v2/infrastructure/storage/ExtractionsStorage";
import { useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { GetSchemaRecordsUseCase } from "~/v2/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v2/domain/usecases/search-records-use-case";

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

    register(V2RecordRepository).withDependency(useAxios).build(),
    register(GetSchemaRecordsUseCase).withDependency(V2RecordRepository).build(),
    register(SearchRecordsUseCase).withDependency(V2RecordRepository).build(),

    register(ProjectionRepository).withDependency(useAxios).build(),
    register(GetWorkspaceProjectionUseCase).withDependencies(ProjectionRepository, useExtractions).build(),
  ];

  Container.register(dependencies);
};
