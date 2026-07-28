import type { AxiosInstance } from "axios";
import { V2Record, type V2RecordStatus } from "~/v2/domain/entities/record/V2Record";
import { RecordsPage } from "~/v2/domain/entities/record/RecordsPage";
import { SearchCriteria } from "~/v2/domain/entities/search/SearchCriteria";

// Hand-written response interfaces (no generated v1 client — see the 20 repositories under
// v1/infrastructure/repositories/ for the same convention).
interface BackendRecord {
  id: string;
  dataset_id: string;
  reference: string | null;
  external_id: string | null;
  fields: Record<string, unknown>;
  metadata: Record<string, unknown> | null;
  status: string;
  inserted_at: string;
  updated_at: string;
}

interface BackendRecords {
  items: BackendRecord[];
  total: number | null;
}

interface BackendSearchRecord {
  record: BackendRecord;
  query_score: number | null;
}

interface BackendSearchRecordsResult {
  items: BackendSearchRecord[];
  total: number;
}

const toRecord = (backend: BackendRecord): V2Record =>
  new V2Record(
    backend.id,
    backend.dataset_id,
    backend.reference,
    backend.external_id ?? null,
    (backend.fields ?? {}) as Record<string, unknown>,
    (backend.metadata ?? null) as Record<string, unknown> | null,
    backend.status as V2RecordStatus,
    backend.inserted_at,
    backend.updated_at
  );

const toPage = (backend: BackendRecords): RecordsPage =>
  new RecordsPage(backend.items.map(toRecord), backend.total ?? 0);

const toPageFromSearch = (backend: BackendSearchRecordsResult): RecordsPage =>
  new RecordsPage(
    backend.items.map((item) => toRecord(item.record)),
    backend.total
  );

// `responses`/`suggestions`/`vectors`/`response_suggestions` — RecordInclude (enums.py).
export type RecordIncludeKey = "responses" | "suggestions" | "vectors" | "response_suggestions";

export interface GetRecordsOptions {
  offset?: number;
  limit?: number;
  reference?: string;
  include?: RecordIncludeKey[];
}

export class V2RecordRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getRecords(schemaId: string, options: GetRecordsOptions = {}): Promise<RecordsPage> {
    const { data } = await this.axios.get<BackendRecords>(`/v1/datasets/${schemaId}/records`, {
      params: {
        offset: options.offset,
        limit: options.limit,
        reference: options.reference,
        include: options.include?.join(","),
      },
    });
    return toPage(data);
  }

  async searchRecords(schemaId: string, criteria: SearchCriteria): Promise<RecordsPage> {
    const { data } = await this.axios.post<BackendSearchRecordsResult>(
      `/v1/datasets/${schemaId}/records/search`,
      criteria.toQueryBody(),
      { params: { offset: criteria.offset, limit: criteria.limit } }
    );
    return toPageFromSearch(data);
  }
}
