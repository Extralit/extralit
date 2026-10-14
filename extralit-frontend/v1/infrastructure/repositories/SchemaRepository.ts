import type { AxiosInstance } from "axios";
import { Schema } from "~/v1/domain/entities/schema/Schema";
import { ColumnMeta, type ReviewOverlay } from "~/v1/domain/entities/schema/ColumnMeta";
import { SchemaVersion } from "~/v1/domain/entities/schema/SchemaVersion";
import { SchemaQuestion, type SchemaQuestionType } from "~/v1/domain/entities/schema/SchemaQuestion";

// Hand-written response interfaces (no generated v1 client — see the 20 repositories under
// v1/infrastructure/repositories/ for the same convention).
interface BackendDataset {
  id: string;
  name: string;
  status: string;
  // Not yet serialized by the server's `Dataset` response schema (api/schemas/v1/datasets.py)
  // even though the DB column exists (models/database.py Dataset.current_schema_version_id) —
  // see task-13-report.md "Issues or concerns". Typed per the authoritative v1 contract.
  current_schema_version_id: string | null;
  settings?: Record<string, unknown>;
  workspace_id: string;
  inserted_at: string;
  updated_at: string;
}

interface BackendDatasets {
  items: BackendDataset[];
}

interface BackendSchemaVersion {
  id: string;
  dataset_id: string;
  version: number;
  object_key: string;
  etag: string;
  checksum: string;
  parent_version_id: string | null;
  created_by: string | null;
  inserted_at: string;
  updated_at: string;
}

interface BackendQuestionSettings {
  type: string;
  columns?: string[] | null;
  [key: string]: unknown;
}

interface BackendQuestion {
  id: string;
  name: string;
  title: string;
  description: string | null;
  required: boolean;
  settings: BackendQuestionSettings;
  dataset_id: string;
  inserted_at: string;
  updated_at: string;
}

interface BackendQuestions {
  items: BackendQuestion[];
}

interface BackendColumnFieldSettings {
  type: string;
  dtype: string;
  nullable: boolean;
  review: ReviewOverlay | null;
}

interface BackendField {
  id: string;
  name: string;
  title: string;
  required: boolean;
  settings: BackendColumnFieldSettings | Record<string, unknown>;
  dataset_id: string;
  inserted_at: string;
  updated_at: string;
}

interface BackendFields {
  items: BackendField[];
}

const toSchema = (backend: BackendDataset): Schema =>
  new Schema(
    backend.id,
    backend.name,
    backend.status,
    backend.workspace_id,
    backend.current_schema_version_id ?? null,
    (backend.settings ?? {}) as Record<string, unknown>,
    backend.inserted_at,
    backend.updated_at
  );

const toVersion = (backend: BackendSchemaVersion): SchemaVersion =>
  new SchemaVersion(backend.id, backend.dataset_id, backend.version, backend.inserted_at);

const toQuestion = (backend: BackendQuestion): SchemaQuestion =>
  new SchemaQuestion(
    backend.id,
    backend.dataset_id,
    backend.name,
    backend.title,
    backend.description ?? null,
    backend.settings.type as SchemaQuestionType,
    backend.settings.columns ?? null,
    (backend.settings ?? {}) as Record<string, unknown>,
    backend.required
  );

export class SchemaRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getSchemas(workspaceId: string): Promise<Schema[]> {
    const { data } = await this.axios.get<BackendDatasets>("/v1/me/datasets", {
      params: { workspace_id: workspaceId },
    });
    // Plain annotation datasets (no Pandera schema attached) don't belong on /schemas.
    return data.items.filter((d) => d.current_schema_version_id !== null).map(toSchema);
  }

  async getSchema(schemaId: string): Promise<Schema> {
    const { data } = await this.axios.get<BackendDataset>(`/v1/datasets/${schemaId}`);
    return toSchema(data);
  }

  async getVersions(schemaId: string): Promise<SchemaVersion[]> {
    const { data } = await this.axios.get<BackendSchemaVersion[]>(`/v1/datasets/${schemaId}/schema-versions`);
    return data.map(toVersion);
  }

  async getQuestions(schemaId: string): Promise<SchemaQuestion[]> {
    const { data } = await this.axios.get<BackendQuestions>(`/v1/datasets/${schemaId}/questions`);
    return data.items.map(toQuestion);
  }

  // Column manifest, replacing the deleted `SchemaVersion.columns_cache` — sourced from the
  // dataset's `Field` rows of settings.type === "column" (v2->v1 fold, api/schemas/v1/fields.py).
  async getColumns(datasetId: string): Promise<ColumnMeta[]> {
    const { data } = await this.axios.get<BackendFields>(`/v1/datasets/${datasetId}/fields`);
    return data.items
      .filter(
        (field): field is BackendField & { settings: BackendColumnFieldSettings } => field.settings?.type === "column"
      )
      .map(
        (field) =>
          new ColumnMeta(
            field.name,
            field.settings.dtype,
            field.settings.nullable ?? true,
            field.settings.review ?? null
          )
      );
  }
}
