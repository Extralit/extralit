import type { IPdfMatchingService, PdfMatchResult, PdfMatchingResult } from "./IPdfMatchingService";
import type { ParsedEntry } from "./IFileService";

interface MatchCandidate {
  entry: ParsedEntry;
  type: string;
  confidence: number;
}

export class PdfMatchingService implements IPdfMatchingService {
  matchFiles(files: File[], entries: ParsedEntry[]): PdfMatchingResult {
    if (!entries || entries.length === 0 || files.length === 0) {
      return {
        matchedFiles: [],
        unmatchedFiles: [...files],
      };
    }

    const matchedFiles: PdfMatchResult[] = [];
    const unmatchedFiles: File[] = [];
    const matchedReferences = new Set<string>();
    const webkitMatchedFiles = new Set<File>();

    // Phase 1: Webkit path matching (highest priority)
    for (const file of files) {
      const webkitMatch = this.findWebkitPathMatch(file, entries);
      if (webkitMatch && !matchedReferences.has(webkitMatch.entry.reference)) {
        matchedFiles.push({
          file,
          bibEntry: webkitMatch.entry,
          matchType: webkitMatch.type,
          confidence: webkitMatch.confidence,
        });
        matchedReferences.add(webkitMatch.entry.reference);
        webkitMatchedFiles.add(file);
      }
    }

    // Phase 2: Other matching methods for remaining files
    const remainingFiles = files.filter((file) => !webkitMatchedFiles.has(file));

    for (const file of remainingFiles) {
      const match = this.findBestNonWebkitMatch(file, entries, matchedReferences);
      if (match) {
        matchedFiles.push({
          file,
          bibEntry: match.entry,
          matchType: match.type,
          confidence: match.confidence,
        });
        matchedReferences.add(match.entry.reference);
      } else {
        unmatchedFiles.push(file);
      }
    }

    // Sort matched files by confidence (highest first)
    matchedFiles.sort((a, b) => b.confidence - a.confidence);

    return {
      matchedFiles,
      unmatchedFiles,
    };
  }

  private findWebkitPathMatch(file: File, entries: ParsedEntry[]): MatchCandidate | null {
    const filePath: string = (file as any).webkitRelativePath || file.name;

    for (const entry of entries) {
      const webkitMatch = this.checkWebkitPathMatch(filePath, entry.filePaths);
      if (webkitMatch) {
        return {
          entry,
          type: webkitMatch.type,
          confidence: webkitMatch.confidence,
        };
      }
    }
    return null;
  }

  private findBestNonWebkitMatch(
    file: File,
    entries: ParsedEntry[],
    matchedReferences: Set<string>
  ): MatchCandidate | null {
    const fileName: string = file.name.toLowerCase().replace(/\.pdf$/, "");
    let bestMatch: MatchCandidate | null = null;
    let bestConfidence = 0;

    for (const entry of entries) {
      if (matchedReferences.has(entry.reference)) {
        continue;
      }

      const matches = [
        this.checkFileFieldMatch(fileName, entry.filePaths),
        this.checkExactMatch(fileName, entry.reference),
        this.checkTitleMatch(fileName, entry.title),
      ].filter(Boolean);

      if (matches.length > 0) {
        const bestFileMatch = matches.reduce((best, current) =>
          current.confidence > best.confidence ? current : best
        );

        if (bestFileMatch.confidence > bestConfidence) {
          bestMatch = {
            entry,
            type: bestFileMatch.type,
            confidence: bestFileMatch.confidence,
          };
          bestConfidence = bestFileMatch.confidence;
        }
      }
    }

    return bestConfidence >= 0.6 ? bestMatch : null;
  }

  private checkWebkitPathMatch(
    filePath: string,
    parsedFilePaths?: string[]
  ): { type: string; confidence: number } | null {
    if (!parsedFilePaths || parsedFilePaths.length === 0) return null;

    const normalizedFilePath = this.normalizePath(filePath);

    for (const bibFilePath of parsedFilePaths) {
      const normalizedBibPath = this.normalizePath(bibFilePath);

      if (normalizedFilePath === normalizedBibPath) {
        return { type: "webkit_path_exact", confidence: 1.0 };
      }

      if (this.checkSuffixPathMatch(normalizedFilePath, normalizedBibPath)) {
        return { type: "webkit_path_suffix", confidence: 0.95 };
      }

      const filePathName = this.extractFileNameFromPath(normalizedFilePath);
      const bibPathName = this.extractFileNameFromPath(normalizedBibPath);

      if (filePathName && bibPathName) {
        const similarity = this.calculateStringSimilarity(filePathName, bibPathName);
        if (similarity >= 0.9) {
          return { type: "webkit_path_filename", confidence: similarity * 0.9 };
        }
      }
    }

    return null;
  }

  private checkFileFieldMatch(
    fileName: string,
    parsedFilePaths?: string[]
  ): { type: string; confidence: number } | null {
    if (!parsedFilePaths || parsedFilePaths.length === 0) return null;

    for (const filePath of parsedFilePaths) {
      const pathFileName = this.extractFileNameFromPath(filePath);
      if (pathFileName) {
        const cleanPathFileName = pathFileName.toLowerCase().replace(/\.pdf$/, "");

        if (fileName === cleanPathFileName) {
          return { type: "file_field_parsed", confidence: 0.95 };
        }

        const similarity = this.calculateStringSimilarity(fileName, cleanPathFileName);
        if (similarity >= 0.8) {
          return { type: "file_field_parsed", confidence: similarity * 0.9 };
        }
      }
    }

    return null;
  }

  private checkExactMatch(fileName: string, reference?: string): { type: string; confidence: number } | null {
    if (!reference) return null;

    const refKey = reference.toLowerCase();
    if (fileName === refKey) {
      return { type: "exact", confidence: 1.0 };
    }
    return null;
  }

  private checkTitleMatch(fileName: string, title?: string): { type: string; confidence: number } | null {
    if (!title) return null;

    const cleanTitle = title
      .toLowerCase()
      .replace(/[^\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    const cleanFileName = fileName
      .replace(/[^\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    const titleWords = cleanTitle.split(" ").filter((word) => word.length > 3);
    const fileWords = cleanFileName.split(" ");

    let matchedWords = 0;
    for (const titleWord of titleWords) {
      if (fileWords.some((fileWord) => fileWord.includes(titleWord) || titleWord.includes(fileWord))) {
        matchedWords++;
      }
    }

    if (titleWords.length > 0) {
      const confidence = matchedWords / titleWords.length;
      if (confidence >= 0.6) {
        return { type: "title", confidence: confidence * 0.8 };
      }
    }

    return null;
  }

  private calculateStringSimilarity(str1: string, str2: string): number {
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;

    if (longer.length === 0) return 1.0;

    const distance = this.levenshteinDistance(longer, shorter);
    return (longer.length - distance) / longer.length;
  }

  private levenshteinDistance(str1: string, str2: string): number {
    const matrix: number[][] = [];

    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(matrix[i - 1][j - 1] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j] + 1);
        }
      }
    }

    return matrix[str2.length][str1.length];
  }

  private normalizePath(path: string): string {
    if (!path) return "";

    return path.toLowerCase().replace(/\\/g, "/").replace(/\/+/g, "/").replace(/^\/*/, "").replace(/\/*$/, "").trim();
  }

  private extractFileNameFromPath(path: string): string | null {
    if (!path) return null;

    const normalizedPath = this.normalizePath(path);
    const parts = normalizedPath.split("/");
    const fileName = parts[parts.length - 1];

    return fileName ? fileName.replace(/\.pdf$/, "") : null;
  }

  private checkSuffixPathMatch(filePath: string, bibPath: string): boolean {
    if (!filePath || !bibPath) return false;

    const filePathParts = filePath.split("/");
    const bibPathParts = bibPath.split("/");
    const minLength = Math.min(filePathParts.length, bibPathParts.length);

    for (let i = 1; i <= minLength; i++) {
      const filePathSuffix = filePathParts.slice(-i).join("/");
      const bibPathSuffix = bibPathParts.slice(-i).join("/");

      if (filePathSuffix === bibPathSuffix) {
        const matchRatio = i / Math.max(filePathParts.length, bibPathParts.length);
        return matchRatio >= 0.5;
      }
    }

    return false;
  }
}
