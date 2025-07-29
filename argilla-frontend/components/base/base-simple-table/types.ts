import { CellComponent } from "tabulator-tables";

export interface SimpleTableColumn {
  field: string;
  title: string;
  width?: number;
  minWidth?: number;
  maxWidth?: number;
  resizable?: boolean;
  sortable?: boolean;
  filterable?: boolean;
  formatter?: string | ((cell: CellComponent, formatterParams: any, onRendered: (callback: () => void) => void) => string | HTMLElement);
  editor?: string | boolean;
  editorParams?: any;
  validator?: string | string[] | ((cell: CellComponent, value: any, parameters: any) => boolean);
  headerFilter?: string | boolean;
  headerFilterParams?: any;
  cellClick?: (e: UIEvent, cell: CellComponent) => void;
  cellDblClick?: (e: UIEvent, cell: CellComponent) => void;
  cssClass?: string;
  headerSort?: boolean;
  visible?: boolean;
}

export interface SimpleTableOptions {
  height?: string | number;
  layout?: "fitData" | "fitDataFill" | "fitDataStretch" | "fitDataTable" | "fitColumns";
  pagination?: boolean;
  paginationSize?: number;
  paginationSizeSelector?: number[] | boolean;
  selectable?: boolean | number | "highlight";
  selectableRangeMode?: "click" | "drag";
  movableRows?: boolean;
  movableColumns?: boolean;
  resizableColumns?: boolean;
  sortMode?: "local" | "remote";
  filterMode?: "local" | "remote";
  placeholder?: string;
}