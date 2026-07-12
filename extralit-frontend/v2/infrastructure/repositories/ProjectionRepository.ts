import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";

type BackendProjectionView = components["schemas"]["ProjectionView"];

export interface ProjectionCellDto {
  questionName: string;
  value: unknown;
  source: "response" | "suggestion" | null;
}

export interface ProjectionRecordDto {
  recordId: string;
  schemaId: string;
  reference: string;
  cells: ProjectionCellDto[];
}

export interface ProjectionViewDto {
  reference: string;
  records: ProjectionRecordDto[];
  totalRecords: number;
}

export class ProjectionRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getProjection(reference: string, workspaceId: string): Promise<ProjectionViewDto> {
    // DOIs contain slashes — always percent-encode the path param (spec §7 / seam B).
    const { data } = await this.axios.get<BackendProjectionView>(
      `/v2/projection/references/${encodeURIComponent(reference)}`,
      { params: { workspace_id: workspaceId } }
    );
    return {
      reference: data.reference,
      totalRecords: data.total_records,
      records: data.records.map((r) => ({
        recordId: r.record_id,
        schemaId: r.schema_id,
        reference: r.reference,
        cells: r.cells.map((c) => ({
          questionName: c.question_name,
          value: c.value ?? null,
          source: (c.source ?? null) as "response" | "suggestion" | null,
        })),
      })),
    };
  }
}
