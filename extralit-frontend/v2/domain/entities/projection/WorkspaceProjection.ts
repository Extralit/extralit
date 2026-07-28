export interface ProjectionColumn {
  name: string; // flat "Dataset.question" / "Dataset.question.subcol"
  datasetId: string;
  datasetName: string;
  questionName: string;
  subColumn: string | null;
  dtype: string;
}

export interface ProjectionGridCell {
  value: unknown;
  source: "response" | "suggestion";
  recordId: string;
  agent: string | null;
  score: number | number[] | null;
}

export interface ProjectionGridRow {
  reference: string;
  rowIndex: number;
  cells: Record<string, ProjectionGridCell>;
}

export class WorkspaceProjection {
  constructor(
    public readonly columns: ProjectionColumn[],
    public readonly rows: ProjectionGridRow[],
    public readonly totalReferences: number
  ) {}
}
