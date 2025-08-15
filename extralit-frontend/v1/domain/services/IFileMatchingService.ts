import { TableData } from "../entities/table/TableData";
import type { ParsedEntry } from "./IFileParsingService";

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
