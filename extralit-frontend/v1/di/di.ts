import type { AxiosInstance } from "axios";
import Container, { register } from "ts-injecty";

import type { IAuthService } from "~/v1/domain/services/IAuthService";

type NuxtAppLike = {
  $axios: AxiosInstance;
  $auth: IAuthService;
  $i18n?: { t: (key: string) => unknown };
};

import { useEventDispatcher } from "@codescouts/events";

import { useTeamProgress } from "../infrastructure/storage/TeamProgressStorage";
import { UpdateMetricsEventHandler, UpdateTeamProgressEventHandler } from "../infrastructure/events";

import { useAxiosExtension } from "@/v1/infrastructure/services/useAxiosExtension";

import {
  DatasetRepository,
  RecordRepository,
  QuestionRepository,
  FieldRepository,
  MetricsRepository,
  MetadataRepository,
  DocumentRepository,
  VectorRepository,
  AgentRepository,
  OAuthRepository,
  EnvironmentRepository,
  WorkspaceRepository,
  AuthRepository,
  UserRepository,
  HubRepository,
  JobRepository,
} from "@/v1/infrastructure/repositories";

import { useLocalStorage, useRole, useRoutes } from "@/v1/infrastructure/services";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";
import { useRecords } from "@/v1/infrastructure/storage/RecordsStorage";
import { useDatasets } from "@/v1/infrastructure/storage/DatasetsStorage";
import { useMetrics } from "@/v1/infrastructure/storage/MetricsStorage";
import { useDatasetSetting } from "@/v1/infrastructure/storage/DatasetSettingStorage";
import { useWorkspaces } from "@/v1/infrastructure/storage/WorkspaceStorage";

import { GetHfDatasetCreationUseCase } from "~/v1/domain/usecases/get-hf-dataset-creation-use-case";
import { GetDatasetsUseCase } from "@/v1/domain/usecases/get-datasets-use-case";
import { GetDatasetByIdUseCase } from "@/v1/domain/usecases/get-dataset-by-id-use-case";
import { GetDocumentByRecordMetadataUseCase } from "~/v1/domain/usecases/get-document-by-record-metadata-use-case";
import { GetDocumentsByWorkspaceUseCase } from "@/v1/domain/usecases/get-documents-by-workspace-use-case";
import { GetLLMExtractionUseCase } from "@/v1/domain/usecases/get-extraction-completion-use-case";
import { GetExtractionSchemaUseCase } from "@/v1/domain/usecases/get-extraction-schema-use-case";
import { GetDatasetProgressUseCase } from "@/v1/domain/usecases/get-dataset-progress-use-case";
import { DeleteDatasetUseCase } from "@/v1/domain/usecases/delete-dataset-use-case";
import { GetRecordsByCriteriaUseCase } from "@/v1/domain/usecases/get-records-by-criteria-use-case";
import { LoadRecordsToAnnotateUseCase } from "@/v1/domain/usecases/load-records-to-annotate-use-case";
import { GetFieldsUseCase } from "@/v1/domain/usecases/get-fields-use-case";
import { SubmitRecordUseCase } from "@/v1/domain/usecases/submit-record-use-case";
import { SaveDraftUseCase } from "@/v1/domain/usecases/save-draft-use-case";
import { BulkAnnotationUseCase } from "@/v1/domain/usecases/bulk-annotation-use-case";
import { DiscardRecordUseCase } from "@/v1/domain/usecases/discard-record-use-case";
import { GetUserMetricsUseCase } from "@/v1/domain/usecases/get-user-metrics-use-case";
import { GetDatasetSettingsUseCase } from "@/v1/domain/usecases/dataset-setting/get-dataset-settings-use-case";
import { UpdateQuestionSettingUseCase } from "@/v1/domain/usecases/dataset-setting/update-question-setting-use-case";
import { UpdateFieldSettingUseCase } from "@/v1/domain/usecases/dataset-setting/update-field-setting-use-case";
import { UpdateDatasetSettingUseCase } from "@/v1/domain/usecases/dataset-setting/update-dataset-setting-use-case";
import { GetMetadataUseCase } from "@/v1/domain/usecases/get-metadata-use-case";
import { GetDatasetVectorsUseCase } from "@/v1/domain/usecases/get-dataset-vectors-use-case";
import { UpdateVectorSettingUseCase } from "@/v1/domain/usecases/dataset-setting/update-vector-setting-use-case";
import { GetDatasetQuestionsFilterUseCase } from "@/v1/domain/usecases/get-dataset-questions-filter-use-case";
import { GetDatasetSuggestionsAgentsUseCase } from "@/v1/domain/usecases/get-dataset-suggestions-agents-use-case";
import { UpdateMetadataSettingUseCase } from "@/v1/domain/usecases/dataset-setting/update-metadata-setting-use-case";
import { OAuthLoginUseCase } from "@/v1/domain/usecases/oauth-login-use-case";
import { GetEnvironmentUseCase } from "@/v1/domain/usecases/get-environment-use-case";
import { GetWorkspacesUseCase } from "@/v1/domain/usecases/get-workspaces-use-case";
import { GetImportCompatibleDatasetsUseCase } from "@/v1/domain/usecases/get-import-compatible-datasets-use-case";
import { GetDatasetQuestionsGroupedUseCase } from "@/v1/domain/usecases/get-dataset-questions-grouped-use-case";
import { GetDatasetFieldsGroupedUseCase } from "@/v1/domain/usecases/get-dataset-fields-grouped-use-case";
import { GetImportAnalysisUseCase } from "@/v1/domain/usecases/get-import-analysis-use-case";
import { CreateImportHistoryUseCase } from "@/v1/domain/usecases/create-import-history-use-case";
import { BulkUploadDocumentsUseCase } from "@/v1/domain/usecases/bulk-upload-documents-use-case";
import { GetImportHistoryUseCase } from "@/v1/domain/usecases/get-import-history-use-case";
import { GetImportHistoryDetailsUseCase } from "@/v1/domain/usecases/get-import-history-details-use-case";
import { GetJobStatusUseCase } from "@/v1/domain/usecases/get-job-status-use-case";
import { LoadUserUseCase } from "@/v1/domain/usecases/load-user-use-case";
import { CreateDatasetUseCase } from "@/v1/domain/usecases/create-dataset-use-case";
import { UpdateDatasetUseCase } from "@/v1/domain/usecases/update-dataset-use-case";
import { GetFirstRecordFromHub } from "@/v1/domain/usecases/get-first-record-from-hub";
import { ExportDatasetToHubUseCase } from "@/v1/domain/usecases/export-dataset-to-hub-use-case";
import { AuthLoginUseCase } from "@/v1/domain/usecases/auth-login-use-case";
import { FileParsingService } from "~/v1/domain/services/FileParsingService";
import { PdfMatchingService } from "@/v1/domain/services/FileMatchingService";

import { SchemaRepository } from "~/v1/infrastructure/repositories/SchemaRepository";
import { SchemaRecordRepository } from "~/v1/infrastructure/repositories/SchemaRecordRepository";
import { ProjectionRepository } from "~/v1/infrastructure/repositories/ProjectionRepository";
import { GetWorkspaceProjectionUseCase } from "~/v1/domain/usecases/get-workspace-projection-use-case";
import { useExtractions } from "~/v1/infrastructure/storage/ExtractionsStorage";
import { useSchemas } from "~/v1/infrastructure/storage/SchemasStorage";
import { GetSchemasUseCase } from "~/v1/domain/usecases/get-schemas-use-case";
import { GetSchemaSettingsUseCase } from "~/v1/domain/usecases/get-schema-settings-use-case";
import { GetSchemaRecordsUseCase } from "~/v1/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v1/domain/usecases/search-records-use-case";

export const loadDependencyContainer = (nuxtApp: NuxtAppLike) => {
  const t = (key: string) => String(nuxtApp.$i18n?.t(key) ?? key);
  const useAxios = useAxiosExtension(nuxtApp.$axios, t);
  const useAuth = () => nuxtApp.$auth;

  const dependencies = [
    register(UpdateMetricsEventHandler).build(),
    register(UpdateTeamProgressEventHandler).build(),
    register(HubRepository).withDependency(useAxios).build(),
    register(DatasetRepository).withDependency(useAxios).build(),
    register(RecordRepository).withDependency(useAxios).build(),
    register(DocumentRepository).withDependency(useAxios).build(),
    register(QuestionRepository).withDependency(useAxios).build(),
    register(FieldRepository).withDependency(useAxios).build(),
    register(MetricsRepository).withDependency(useAxios).build(),
    register(MetadataRepository).withDependency(useAxios).build(),
    register(VectorRepository).withDependency(useAxios).build(),
    register(AgentRepository).withDependency(useAxios).build(),
    register(WorkspaceRepository).withDependency(useAxios).build(),
    register(JobRepository).withDependency(useAxios).build(),

    register(OAuthRepository).withDependencies(useAxios, useRoutes).build(),
    register(EnvironmentRepository).withDependency(useAxios).build(),
    register(AuthRepository).withDependency(useAxios).build(),
    register(UserRepository).withDependency(useAxios).build(),

    register(GetHfDatasetCreationUseCase).withDependency(HubRepository).build(),

    register(DeleteDatasetUseCase).withDependency(DatasetRepository).build(),

    register(GetWorkspacesUseCase).withDependencies(WorkspaceRepository, useWorkspaces).build(),

    register(GetImportCompatibleDatasetsUseCase).withDependency(useAxios).build(),

    register(GetDatasetsUseCase).withDependencies(DatasetRepository, useDatasets).build(),

    register(GetDocumentByRecordMetadataUseCase).withDependencies(DocumentRepository, useDocument).build(),

    register(GetDocumentsByWorkspaceUseCase).withDependency(DocumentRepository).build(),

    register(GetDatasetByIdUseCase).withDependencies(DatasetRepository, useDataset).build(),

    register(GetDatasetProgressUseCase).withDependencies(DatasetRepository, useTeamProgress).build(),

    register(GetLLMExtractionUseCase).withDependency(useAxios).build(),

    register(GetExtractionSchemaUseCase).withDependency(useAxios).build(),

    register(GetImportAnalysisUseCase).withDependency(useAxios).build(),

    register(CreateImportHistoryUseCase).withDependency(useAxios).build(),

    register(BulkUploadDocumentsUseCase).withDependency(useAxios).build(),

    register(GetImportHistoryUseCase).withDependency(useAxios).build(),

    register(GetImportHistoryDetailsUseCase).withDependency(useAxios).build(),

    register(GetJobStatusUseCase).withDependency(useAxios).build(),

    register(GetRecordsByCriteriaUseCase)
      .withDependencies(RecordRepository, QuestionRepository, FieldRepository, useRecords)
      .build(),

    register(GetUserMetricsUseCase).withDependencies(MetricsRepository, useMetrics).build(),

    register(LoadRecordsToAnnotateUseCase)
      .withDependencies(GetRecordsByCriteriaUseCase, GetDatasetProgressUseCase, GetUserMetricsUseCase, useRecords)
      .build(),

    register(GetFieldsUseCase).withDependency(FieldRepository).build(),

    register(DiscardRecordUseCase).withDependencies(RecordRepository, useEventDispatcher).build(),

    register(SubmitRecordUseCase).withDependencies(RecordRepository, useEventDispatcher).build(),

    register(SaveDraftUseCase).withDependencies(RecordRepository, useEventDispatcher).build(),

    register(BulkAnnotationUseCase)
      .withDependencies(GetRecordsByCriteriaUseCase, LoadRecordsToAnnotateUseCase, RecordRepository, useEventDispatcher)
      .build(),

    register(GetDatasetSettingsUseCase)
      .withDependencies(
        useRole,
        DatasetRepository,
        QuestionRepository,
        FieldRepository,
        VectorRepository,
        MetadataRepository,
        useDatasetSetting
      )
      .build(),

    register(UpdateQuestionSettingUseCase).withDependency(QuestionRepository).build(),

    register(UpdateFieldSettingUseCase).withDependency(FieldRepository).build(),

    register(UpdateDatasetSettingUseCase).withDependency(DatasetRepository).build(),

    register(UpdateVectorSettingUseCase).withDependency(VectorRepository).build(),

    register(UpdateMetadataSettingUseCase).withDependency(MetadataRepository).build(),

    register(GetMetadataUseCase).withDependency(MetadataRepository).build(),

    register(GetDatasetVectorsUseCase).withDependency(VectorRepository).build(),

    register(GetDatasetQuestionsFilterUseCase).withDependency(QuestionRepository).build(),

    register(GetDatasetQuestionsGroupedUseCase).withDependency(QuestionRepository).build(),

    register(GetDatasetFieldsGroupedUseCase).withDependency(FieldRepository).build(),

    register(GetDatasetSuggestionsAgentsUseCase).withDependency(AgentRepository).build(),

    register(GetEnvironmentUseCase).withDependency(EnvironmentRepository).build(),

    register(LoadUserUseCase).withDependencies(useAuth, UserRepository).build(),

    register(OAuthLoginUseCase).withDependencies(useAuth, OAuthRepository, LoadUserUseCase).build(),

    register(AuthLoginUseCase).withDependencies(useAuth, AuthRepository, LoadUserUseCase).build(),

    register(CreateDatasetUseCase)
      .withDependencies(DatasetRepository, WorkspaceRepository, QuestionRepository, FieldRepository, MetadataRepository)
      .build(),

    register(UpdateDatasetUseCase).withDependency(DatasetRepository).build(),

    register(GetFirstRecordFromHub).withDependency(HubRepository).build(),

    register(ExportDatasetToHubUseCase).withDependencies(DatasetRepository, useLocalStorage).build(),

    register(FileParsingService).build(),
    register(PdfMatchingService).build(),

    register(SchemaRepository).withDependency(useAxios).build(),
    register(GetSchemasUseCase).withDependencies(SchemaRepository, useSchemas).build(),
    register(GetSchemaSettingsUseCase).withDependency(SchemaRepository).build(),

    register(SchemaRecordRepository).withDependency(useAxios).build(),
    register(GetSchemaRecordsUseCase).withDependency(SchemaRecordRepository).build(),
    register(SearchRecordsUseCase).withDependency(SchemaRecordRepository).build(),

    register(ProjectionRepository).withDependency(useAxios).build(),
    register(GetWorkspaceProjectionUseCase).withDependencies(ProjectionRepository, useExtractions).build(),
  ];

  Container.register(dependencies);
};
