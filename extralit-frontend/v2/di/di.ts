import type { AxiosInstance } from "axios";
import Container, { register } from "ts-injecty";

import { useAxiosExtension } from "@/v1/infrastructure/services/useAxiosExtension";

import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";
import { AnnotationRepository } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { ProjectionRepository } from "~/v2/infrastructure/repositories/ProjectionRepository";
import { GetWorkspaceProjectionUseCase } from "~/v2/domain/usecases/get-workspace-projection-use-case";
import { useExtractions } from "~/v2/infrastructure/storage/ExtractionsStorage";
import { SubmitReferenceReviewUseCase } from "~/v2/domain/usecases/submit-reference-review-use-case";
import { SaveReviewDraftUseCase } from "~/v2/domain/usecases/save-review-draft-use-case";
import { DiscardReviewUseCase } from "~/v2/domain/usecases/discard-review-use-case";
import { useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { GetSchemaRecordsUseCase } from "~/v2/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v2/domain/usecases/search-records-use-case";
import { RebuildSchemaIndexUseCase } from "~/v2/domain/usecases/rebuild-schema-index-use-case";

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
    register(RebuildSchemaIndexUseCase).withDependency(V2RecordRepository).build(),

    register(AnnotationRepository).withDependency(useAxios).build(),
    register(ProjectionRepository).withDependency(useAxios).build(),
    register(GetWorkspaceProjectionUseCase).withDependencies(ProjectionRepository, useExtractions).build(),

    register(SubmitReferenceReviewUseCase).withDependency(AnnotationRepository).build(),
    register(SaveReviewDraftUseCase).withDependency(AnnotationRepository).build(),
    register(DiscardReviewUseCase).withDependency(AnnotationRepository).build(),
  ];

  Container.register(dependencies);
};
