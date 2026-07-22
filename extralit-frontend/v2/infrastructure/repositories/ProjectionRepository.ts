import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";
import { type ProjectionColumn, type ProjectionGridRow } from "../../domain/entities/projection/WorkspaceProjection";

type BackendProjectionView = components["schemas"]["ProjectionView"];
type BackendWorkspaceProjection = components["schemas"]["WorkspaceProjection"];

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

export interface WorkspaceProjectionPageDto {
  columns: ProjectionColumn[];
  rows: ProjectionGridRow[];
  totalReferences: number;
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

  async getWorkspaceProjection(workspaceId: string, offset = 0, limit = 50): Promise<WorkspaceProjectionPageDto> {
    const { data } = await this.axios.get<BackendWorkspaceProjection>("/v2/projection", {
      params: { workspace_id: workspaceId, offset, limit },
    });
    return {
      // Column order is server-defined (schema definition order, not alphabetical) — preserve as-is.
      columns: data.columns.map((c) => ({
        name: c.name,
        schemaId: c.schema_id,
        schemaName: c.schema_name,
        questionName: c.question_name,
        subColumn: c.sub_column ?? null,
        dtype: c.dtype,
      })),
      rows: data.rows.map((r) => ({
        reference: r.reference,
        rowIndex: r.row_index,
        cells: Object.fromEntries(
          Object.entries(r.cells).map(([columnName, cell]) => [
            columnName,
            {
              value: cell.value ?? null,
              source: cell.source,
              recordId: cell.record_id,
              agent: cell.agent ?? null,
              score: cell.score ?? null,
            },
          ])
        ),
      })),
      totalReferences: data.total_references,
    };
  }
}
