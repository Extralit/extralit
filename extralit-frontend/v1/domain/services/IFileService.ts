import type { DataframeData } from "~/v1/domain/entities/import/ImportAnalysis";

export interface ParsedEntry {
  reference: string;
  type: string;
  filePaths?: string[];
  [key: string]: any;
}

export interface ParseResult {
  entries: ParsedEntry[];
  dataframeData: DataframeData;
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

export interface IFileService {
  parseBibTeX(content: string): Promise<ParseResult>;
  parseCSVForPreview(content: string): Promise<CSVPreviewData>;
  parseCSVWithConfig(rawData: Record<string, any>[], config: CSVConfig): Promise<ParseResult>;
  readFileContent(file: File): Promise<string>;
  isValidFileType(file: File, validExtensions: string[]): boolean;
}
