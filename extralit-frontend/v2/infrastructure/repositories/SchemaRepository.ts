import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { ColumnMeta, type ReviewOverlay } from "~/v2/domain/entities/schema/ColumnMeta";
import { SchemaVersion } from "~/v2/domain/entities/schema/SchemaVersion";
import { Question, type QuestionType } from "~/v2/domain/entities/question/Question";

type BackendSchema = components["schemas"]["SchemaRead"];
type BackendSchemas = components["schemas"]["Schemas"];
type BackendVersion = components["schemas"]["SchemaVersionRead"];
type BackendQuestions = components["schemas"]["Questions"];
type BackendQuestion = components["schemas"]["QuestionRead"];

const toSchema = (backend: BackendSchema): Schema =>
  new Schema(
    backend.id,
    backend.name,
    backend.status,
    backend.workspace_id,
    backend.current_version_id ?? null,
    (backend.settings ?? {}) as Record<string, unknown>,
    backend.inserted_at,
    backend.updated_at
  );

const toVersion = (backend: BackendVersion): SchemaVersion =>
  new SchemaVersion(
    backend.id,
    backend.schema_id,
    backend.version,
    // columns_cache is an opaque JSONB array in the generated types (Record<string, never>[]);
    // bridge through unknown to the concrete per-column shape the server actually emits.
    (
      (backend.columns_cache ?? []) as unknown as {
        name: string;
        dtype: string;
        nullable: boolean;
        review?: ReviewOverlay | null;
      }[]
    ).map((c) => new ColumnMeta(c.name, c.dtype, c.nullable, c.review ?? null)),
    (backend.review_widgets ?? {}) as Record<string, Record<string, unknown>>,
    backend.inserted_at
  );

const toQuestion = (backend: BackendQuestion): Question =>
  new Question(
    backend.id,
    backend.schema_id,
    backend.name,
    backend.title,
    backend.description ?? null,
    backend.type as QuestionType,
    backend.columns,
    (backend.settings ?? {}) as Record<string, unknown>,
    backend.required
  );

export class SchemaRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getSchemas(workspaceId: string): Promise<Schema[]> {
    const { data } = await this.axios.get<BackendSchemas>("/v2/schemas", { params: { workspace_id: workspaceId } });
    return data.items.map(toSchema);
  }

  async getSchema(schemaId: string): Promise<Schema> {
    const { data } = await this.axios.get<BackendSchema>(`/v2/schemas/${schemaId}`);
    return toSchema(data);
  }

  async getVersions(schemaId: string): Promise<SchemaVersion[]> {
    const { data } = await this.axios.get<BackendVersion[]>(`/v2/schemas/${schemaId}/versions`);
    return data.map(toVersion);
  }

  async getQuestions(schemaId: string): Promise<Question[]> {
    const { data } = await this.axios.get<BackendQuestions>(`/v2/schemas/${schemaId}/questions`);
    return data.items.map(toQuestion);
  }
}
