import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";
import { V2Record, type V2RecordStatus } from "~/v2/domain/entities/record/V2Record";
import { RecordsPage } from "~/v2/domain/entities/record/RecordsPage";
import { SearchCriteria } from "~/v2/domain/entities/search/SearchCriteria";

type BackendRecord = components["schemas"]["RecordRead"];
type BackendRecords = components["schemas"]["Records"];

const toRecord = (backend: BackendRecord): V2Record =>
  new V2Record(
    backend.id,
    backend.schema_id,
    backend.schema_version_id,
    backend.reference,
    backend.external_id ?? null,
    (backend.fields ?? {}) as Record<string, unknown>,
    (backend.metadata ?? null) as Record<string, unknown> | null,
    backend.status as V2RecordStatus,
    backend.inserted_at,
    backend.updated_at
  );

const toPage = (backend: BackendRecords): RecordsPage => new RecordsPage(backend.items.map(toRecord), backend.total);

export interface GetRecordsOptions {
  offset?: number;
  limit?: number;
  status?: V2RecordStatus;
  reference?: string;
}

export class V2RecordRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getRecords(schemaId: string, options: GetRecordsOptions = {}): Promise<RecordsPage> {
    const { data } = await this.axios.get<BackendRecords>(`/v2/schemas/${schemaId}/records`, { params: options });
    return toPage(data);
  }

  async searchRecords(schemaId: string, criteria: SearchCriteria): Promise<RecordsPage> {
    const { data } = await this.axios.post<BackendRecords>(
      `/v2/schemas/${schemaId}/records:search`,
      criteria.toQueryBody()
    );
    return toPage(data);
  }

  async rebuildIndex(schemaId: string): Promise<number> {
    const { data } = await this.axios.post<{ indexed: number }>(`/v2/schemas/${schemaId}:rebuild-index`);
    return data.indexed;
  }
}
