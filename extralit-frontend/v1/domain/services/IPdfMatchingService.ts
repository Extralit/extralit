import type { ParsedEntry } from "./IFileService";

export interface PdfMatchResult {
  file: File;
  bibEntry: ParsedEntry;
  matchType: string;
  confidence: number;
}

export interface PdfMatchingResult {
  matchedFiles: PdfMatchResult[];
  unmatchedFiles: File[];
}

export interface IPdfMatchingService {
  matchFiles(files: File[], entries: ParsedEntry[]): PdfMatchingResult;
}
