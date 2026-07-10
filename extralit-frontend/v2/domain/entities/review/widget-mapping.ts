import { type ColumnMeta } from "../schema/ColumnMeta";

// Cell editors for table-question sub-columns and read-only context fields (spec §6.2/§6.3).
// Question-level widgets (§6.1) come straight from question.type — see ReviewCellInput.
export type CellEditor = "text" | "number" | "checkbox" | "date";

const KNOWN_EDITORS: CellEditor[] = ["text", "number", "checkbox", "date"];

export const dtypeDefaultEditor = (dtype: string): CellEditor => {
  if (dtype.startsWith("int") || dtype.startsWith("float")) return "number";
  if (dtype === "bool") return "checkbox";
  if (dtype.startsWith("datetime")) return "date";
  return "text"; // str and anything unknown
};

export const columnCellEditor = (column: ColumnMeta): CellEditor => {
  const hinted = column.review?.type;
  if (hinted && (KNOWN_EDITORS as string[]).includes(hinted)) return hinted as CellEditor;
  return dtypeDefaultEditor(column.dtype);
};

// Same precedence for non-question context fields; separate name so call sites read as §6.3.
export const contextRenderer = (column: ColumnMeta): CellEditor => columnCellEditor(column);
