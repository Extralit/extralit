import type { AxiosInstance } from "axios";
import { type ProjectionColumn, type ProjectionGridRow } from "../../domain/entities/projection/WorkspaceProjection";

// Hand-written response interfaces (no generated v1 client — see the 20 repositories under
// v1/infrastructure/repositories/ for the same convention).
interface BackendWorkspaceProjectionColumn {
  name: string;
  dataset_id: string;
  dataset_name: string;
  question_name: string;
  sub_column: string | null;
  dtype: string;
}

interface BackendWorkspaceProjectionCell {
  value: unknown;
  source: "response" | "suggestion";
  record_id: string;
  agent: string | null;
  score: number | number[] | null;
}

interface BackendWorkspaceProjectionRow {
  reference: string;
  row_index: number;
  cells: Record<string, BackendWorkspaceProjectionCell>;
}

interface BackendWorkspaceProjection {
  columns: BackendWorkspaceProjectionColumn[];
  rows: BackendWorkspaceProjectionRow[];
  total_references: number;
}

export interface WorkspaceProjectionPageDto {
  columns: ProjectionColumn[];
  rows: ProjectionGridRow[];
  totalReferences: number;
}

export class ProjectionRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getWorkspaceProjection(workspaceId: string, offset = 0, limit = 50): Promise<WorkspaceProjectionPageDto> {
    const { data } = await this.axios.get<BackendWorkspaceProjection>("/v1/me/datasets/projection", {
      params: { workspace_id: workspaceId, offset, limit },
    });
    return {
      // Column order is server-defined (schema definition order, not alphabetical) — preserve as-is.
      columns: data.columns.map((c) => ({
        name: c.name,
        datasetId: c.dataset_id,
        datasetName: c.dataset_name,
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
