import type { ParsedEntry } from "./IFileParsingService";
import { TableData } from "../entities/table/TableData";

export interface FileMatchResult {
  file: File;
  bibEntry: ParsedEntry;
  matchType: string;
  confidence: number;
}

export interface FileMatchingResult {
  matchedFiles: FileMatchResult[];
  unmatchedFiles: File[];
}

export interface IFileMatchingService {
  matchFiles(files: File[], dataframeData: TableData | null): FileMatchingResult;
}
