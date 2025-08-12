import type { IFileMatchingService, FileMatchResult, FileMatchingResult } from "./IFileMatchingService";
import type { ParsedEntry } from "./IFileService";

interface MatchCandidate {
  entry: ParsedEntry;
  type: string;
  confidence: number;
}

interface PrefixMatchResult {
  prefixLength: number;
  confidence: number;
  type: string;
}

export class PdfMatchingService implements IFileMatchingService {
  matchFiles(files: File[], entries: ParsedEntry[]): FileMatchingResult {
    if (!entries || entries.length === 0 || files.length === 0) {
      return {
        matchedFiles: [],
        unmatchedFiles: [...files],
      };
    }

    const matchedFiles: FileMatchResult[] = [];
    const unmatchedFiles: File[] = [];

    // Track which references have been matched to support multiple files per reference
    const referenceFileCount = new Map<string, number>();
    const processedFiles = new Set<File>();

    // Phase 1: Maximum prefix path matching (highest priority)
    const prefixMatches = this.findMaximumPrefixMatches(files, entries);

    for (const match of prefixMatches) {
      if (!processedFiles.has(match.file)) {
        matchedFiles.push({
          file: match.file,
          bibEntry: match.entry,
          matchType: match.type,
          confidence: match.confidence,
        });

        // Track multiple files per reference
        const currentCount = referenceFileCount.get(match.entry.reference) || 0;
        referenceFileCount.set(match.entry.reference, currentCount + 1);
        processedFiles.add(match.file);
      }
    }

    // Phase 2: Webkit path matching for remaining files
    const remainingFiles = files.filter((file) => !processedFiles.has(file));

    for (const file of remainingFiles) {
      const webkitMatch = this.findWebkitPathMatch(file, entries);
      if (webkitMatch) {
        matchedFiles.push({
          file,
          bibEntry: webkitMatch.entry,
          matchType: webkitMatch.type,
          confidence: webkitMatch.confidence,
        });

        const currentCount = referenceFileCount.get(webkitMatch.entry.reference) || 0;
        referenceFileCount.set(webkitMatch.entry.reference, currentCount + 1);
        processedFiles.add(file);
      }
    }

    // Phase 3: Other matching methods for remaining files
    const finalRemainingFiles = files.filter((file) => !processedFiles.has(file));

    for (const file of finalRemainingFiles) {
      const match = this.findBestNonWebkitMatch(file, entries);
      if (match) {
        matchedFiles.push({
          file,
          bibEntry: match.entry,
          matchType: match.type,
          confidence: match.confidence,
        });

        const currentCount = referenceFileCount.get(match.entry.reference) || 0;
        referenceFileCount.set(match.entry.reference, currentCount + 1);
        processedFiles.add(file);
      } else {
        unmatchedFiles.push(file);
      }
    }

    // Sort matched files by confidence (highest first), then by reference for grouping
    matchedFiles.sort((a, b) => {
      if (Math.abs(a.confidence - b.confidence) < 0.01) {
        return a.bibEntry.reference.localeCompare(b.bibEntry.reference);
      }
      return b.confidence - a.confidence;
    });

    return {
      matchedFiles,
      unmatchedFiles,
    };
  }

  /**
   * Find maximum prefix path matches for all files against all entries
   * This method implements the core maximum prefix matching algorithm
   */
  private findMaximumPrefixMatches(
    files: File[],
    entries: ParsedEntry[]
  ): Array<{
    file: File;
    entry: ParsedEntry;
    type: string;
    confidence: number;
  }> {
    const matches: Array<{
      file: File;
      entry: ParsedEntry;
      type: string;
      confidence: number;
    }> = [];

    // Create a map of all possible file-entry combinations with their prefix match scores
    const allCombinations: Array<{
      file: File;
      entry: ParsedEntry;
      prefixResult: PrefixMatchResult;
    }> = [];

    for (const file of files) {
      const filePath: string = (file as any).webkitRelativePath || file.name;
      const normalizedFilePath = this.normalizePath(filePath);

      for (const entry of entries) {
        if (!entry.filePaths || entry.filePaths.length === 0) continue;

        for (const bibFilePath of entry.filePaths) {
          const normalizedBibPath = this.normalizePath(bibFilePath);
          const prefixResult = this.calculateMaximumPrefixMatch(normalizedFilePath, normalizedBibPath);

          if (prefixResult.prefixLength > 0) {
            allCombinations.push({
              file,
              entry,
              prefixResult,
            });
          }
        }
      }
    }

    // Sort by prefix length (descending) and confidence (descending)
    allCombinations.sort((a, b) => {
      if (a.prefixResult.prefixLength !== b.prefixResult.prefixLength) {
        return b.prefixResult.prefixLength - a.prefixResult.prefixLength;
      }
      return b.prefixResult.confidence - a.prefixResult.confidence;
    });

    // Progressive file addition with deduplication
    const usedFiles = new Set<File>();
    const referenceFileCounts = new Map<string, number>();

    for (const combination of allCombinations) {
      const { file, entry, prefixResult } = combination;

      // Skip if file is already matched with higher confidence
      if (usedFiles.has(file)) continue;

      // Allow multiple files per reference, but ensure quality matches
      const currentFileCount = referenceFileCounts.get(entry.reference) || 0;

      // For multiple files per reference, require higher confidence
      const minConfidence = currentFileCount === 0 ? 0.7 : 0.8;

      if (prefixResult.confidence >= minConfidence) {
        matches.push({
          file,
          entry,
          type: prefixResult.type,
          confidence: prefixResult.confidence,
        });

        usedFiles.add(file);
        referenceFileCounts.set(entry.reference, currentFileCount + 1);
      }
    }

    return matches;
  }

  /**
   * Calculate maximum prefix match between two normalized paths
   */
  private calculateMaximumPrefixMatch(filePath: string, bibPath: string): PrefixMatchResult {
    if (!filePath || !bibPath) {
      return { prefixLength: 0, confidence: 0, type: "no_match" };
    }

    // Split paths into components
    const filePathParts = filePath.split("/").filter((part) => part.length > 0);
    const bibPathParts = bibPath.split("/").filter((part) => part.length > 0);

    // Find maximum prefix match from the end (most specific parts first)
    let maxPrefixLength = 0;
    let matchType = "no_match";

    // Check for exact path match first
    if (filePath === bibPath) {
      return {
        prefixLength: Math.max(filePathParts.length, bibPathParts.length),
        confidence: 1.0,
        type: "exact_path_match",
      };
    }

    // Check suffix matching (from the end of the path)
    const minLength = Math.min(filePathParts.length, bibPathParts.length);

    for (let i = 1; i <= minLength; i++) {
      const filePathSuffix = filePathParts.slice(-i);
      const bibPathSuffix = bibPathParts.slice(-i);

      let allMatch = true;
      for (let j = 0; j < i; j++) {
        if (filePathSuffix[j] !== bibPathSuffix[j]) {
          allMatch = false;
          break;
        }
      }

      if (allMatch) {
        maxPrefixLength = i;
        matchType = i === minLength ? "full_suffix_match" : "partial_suffix_match";
      } else {
        break; // Stop at first non-match since we're looking for continuous suffix
      }
    }

    // If no exact suffix match, try filename similarity
    if (maxPrefixLength === 0) {
      const fileName = filePathParts[filePathParts.length - 1];
      const bibFileName = bibPathParts[bibPathParts.length - 1];

      if (fileName && bibFileName) {
        // Remove .pdf extension for comparison
        const cleanFileName = fileName.replace(/\.pdf$/i, "");
        const cleanBibFileName = bibFileName.replace(/\.pdf$/i, "");

        const similarity = this.calculateStringSimilarity(cleanFileName, cleanBibFileName);
        if (similarity >= 0.8) {
          return {
            prefixLength: 1,
            confidence: similarity * 0.7, // Lower confidence for filename-only matches
            type: "filename_similarity",
          };
        }
      }
    }

    // Calculate confidence based on prefix length and path lengths
    if (maxPrefixLength > 0) {
      const maxPathLength = Math.max(filePathParts.length, bibPathParts.length);
      const minPathLength = Math.min(filePathParts.length, bibPathParts.length);

      // Base confidence on how much of the shorter path is matched
      let confidence = maxPrefixLength / minPathLength;

      // Bonus for matching more of the longer path
      const longerPathBonus = (maxPrefixLength / maxPathLength) * 0.2;
      confidence = Math.min(1.0, confidence + longerPathBonus);

      // Penalty for very different path lengths
      const lengthDifference = Math.abs(filePathParts.length - bibPathParts.length);
      const lengthPenalty = lengthDifference * 0.1;
      confidence = Math.max(0.1, confidence - lengthPenalty);

      return {
        prefixLength: maxPrefixLength,
        confidence,
        type: matchType,
      };
    }

    return { prefixLength: 0, confidence: 0, type: "no_match" };
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

  private findBestNonWebkitMatch(file: File, entries: ParsedEntry[]): MatchCandidate | null {
    const fileName: string = file.name.toLowerCase().replace(/\.pdf$/, "");
    let bestMatch: MatchCandidate | null = null;
    let bestConfidence = 0;

    for (const entry of entries) {
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

      // Use the same maximum prefix matching logic for consistency
      const prefixResult = this.calculateMaximumPrefixMatch(normalizedFilePath, normalizedBibPath);

      if (prefixResult.confidence >= 0.8) {
        return {
          type: `webkit_${prefixResult.type}`,
          confidence: prefixResult.confidence * 0.95, // Slightly lower than maximum prefix matches
        };
      }

      // Fallback to filename similarity for webkit paths
      const filePathName = this.extractFileNameFromPath(normalizedFilePath);
      const bibPathName = this.extractFileNameFromPath(normalizedBibPath);

      if (filePathName && bibPathName) {
        const similarity = this.calculateStringSimilarity(filePathName, bibPathName);
        if (similarity >= 0.9) {
          return { type: "webkit_path_filename", confidence: similarity * 0.85 };
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
}
