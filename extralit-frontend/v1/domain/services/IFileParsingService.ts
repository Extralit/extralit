import { TableData } from "../entities/table/TableData";

export interface ParsedEntry {
  reference: string;
  type: string;
  filePaths?: string[];
  [key: string]: any;
}

export interface CSVConfig {
  referenceColumn: string;
  filesColumn?: string;
}

export interface CSVPreviewData {
  columns: string[];
  previewRows: Record<string, any>[];
  rawData: Record<string, any>[];
}

export interface IFileParsingService {
  parseBibTeX(content: string): Promise<TableData>;
  parseCSVForPreview(content: string): Promise<CSVPreviewData>;
  parseCSVWithConfig(rawData: Record<string, any>[], config: CSVConfig): Promise<TableData>;
  readFileContent(file: File): Promise<string>;
  isValidFileType(file: File, validExtensions: string[]): boolean;
}
