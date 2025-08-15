import { TableData } from "../entities/table/TableData";
import type { IFileMatchingService, FileMatchResult, FileMatchingResult } from "./IFileMatchingService";
import type { ParsedEntry } from "./IFileParsingService";

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
  matchFiles(files: File[], dataframeData: TableData): FileMatchingResult {
    // @ts-ignore
    const entries: ParsedEntry[] = dataframeData?.data || [];

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
    // Track which files have been used to ensure one-to-one file-to-bib-entry matching
    const usedFiles = new Set<File>();

    // Phase 1: Maximum prefix path matching for entries with file attributes
    const prefixMatches = this.findMaximumPrefixMatches(files, entries, usedFiles);

    for (const match of prefixMatches) {
      if (!usedFiles.has(match.file)) {
        matchedFiles.push({
          file: match.file,
          bibEntry: match.entry,
          matchType: match.type,
          confidence: match.confidence,
        });

        // Track multiple files per reference
        const currentCount = referenceFileCount.get(match.entry.reference) || 0;
        referenceFileCount.set(match.entry.reference, currentCount + 1);
        usedFiles.add(match.file); // Mark file as used
      }
    }

    // Phase 2: Exact matching for remaining files against all entries
    const remainingFiles = files.filter((file) => !usedFiles.has(file));

    for (const file of remainingFiles) {
      const exactMatch = this.findExactMatch(file, entries, usedFiles);
      if (exactMatch) {
        matchedFiles.push({
          file,
          bibEntry: exactMatch.entry,
          matchType: exactMatch.type,
          confidence: exactMatch.confidence,
        });

        const currentCount = referenceFileCount.get(exactMatch.entry.reference) || 0;
        referenceFileCount.set(exactMatch.entry.reference, currentCount + 1);
        usedFiles.add(file); // Mark file as used
      }
    }

    // Add remaining unmatched files
    const finalRemainingFiles = files.filter((file) => !usedFiles.has(file));
    unmatchedFiles.push(...finalRemainingFiles);

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
   * Find maximum prefix path matches for entries with file attributes
   */
  private findMaximumPrefixMatches(
    files: File[],
    entries: ParsedEntry[],
    usedFiles: Set<File> = new Set()
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

    // Only process entries that have file attributes
    const entriesWithFiles = entries.filter((entry) => entry.filePaths && entry.filePaths.length > 0);

    if (entriesWithFiles.length === 0) {
      return matches;
    }

    // Create a map of all possible file-entry combinations with their prefix match scores
    const allCombinations: Array<{
      file: File;
      entry: ParsedEntry;
      prefixResult: PrefixMatchResult;
    }> = [];

    for (const file of files) {
      // Skip files that are already matched
      if (usedFiles.has(file)) continue;

      const filePath: string = (file as any).webkitRelativePath || file.name;
      const importFilePath = this.normalizePath(filePath);

      for (const entry of entriesWithFiles) {
        for (const bibFilePath of entry.filePaths) {
          const importBibPath = this.normalizePath(bibFilePath);
          const prefixResult = this.calculateMaximumPrefixMatch(importFilePath, importBibPath);

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
    const localUsedFiles = new Set<File>();
    const referenceFileCounts = new Map<string, number>();

    for (const combination of allCombinations) {
      const { file, entry, prefixResult } = combination;

      // Skip if file is already matched with higher confidence
      if (localUsedFiles.has(file)) continue;

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

        localUsedFiles.add(file);
        referenceFileCounts.set(entry.reference, currentFileCount + 1);
      }
    }

    return matches;
  }

  /**
   * Find exact matches for remaining files against all entries
   */
  private findExactMatch(file: File, entries: ParsedEntry[], usedFiles: Set<File> = new Set()): MatchCandidate | null {
    // Skip if file is already matched
    if (usedFiles.has(file)) {
      return null;
    }

    const fileName: string = file.name.toLowerCase().replace(/\.pdf$/, "");
    let bestMatch: MatchCandidate | null = null;
    let bestConfidence = 0;

    for (const entry of entries) {
      const matches = [
        this.checkReferenceSubstringMatch(fileName, entry.reference),
        this.checkTitleSubstringMatch(fileName, entry.title),
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

    return bestConfidence >= 0.9 ? bestMatch : null;
  }

  /**
   * Check if filename contains the reference as a substring
   */
  private checkReferenceSubstringMatch(
    fileName: string,
    reference?: string
  ): { type: string; confidence: number } | null {
    if (!reference) return null;

    const refKey = reference.toLowerCase();

    // Check for exact match first
    if (fileName === refKey) {
      return { type: "exact_reference", confidence: 1.0 };
    }

    // Check if filename contains reference as substring, but only if it's a significant match
    if (fileName.includes(refKey)) {
      // Calculate how much of the filename the reference represents
      const referenceRatio = refKey.length / fileName.length;

      // Only accept if reference represents at least 60% of the filename
      // This prevents short references from matching long filenames inappropriately
      if (referenceRatio >= 0.6) {
        return { type: "reference_substring", confidence: 0.9 };
      }

      // For less significant matches, reduce confidence
      if (referenceRatio >= 0.4) {
        return { type: "reference_substring", confidence: 0.7 };
      }
    }

    return null;
  }

  /**
   * Check if filename contains normalized title words as substrings
   */
  private checkTitleSubstringMatch(fileName: string, title?: string): { type: string; confidence: number } | null {
    if (!title) return null;

    const cleanTitle = title
      .toLowerCase()
      .replace(/[_\-\s]+/g, " ")
      .trim();

    const cleanFileName = fileName.replace(/[_\-\s]+/g, " ").trim();

    // Check for exact match first
    if (cleanFileName === cleanTitle) {
      return { type: "exact_title", confidence: 1.0 };
    }

    // Split title into words and check if filename contains each word
    const titleWords = cleanTitle.split(" ").filter((word) => word.length > 2);

    if (titleWords.length === 0) return null;

    let matchedWords = 0;
    for (const titleWord of titleWords) {
      if (cleanFileName.includes(titleWord)) {
        matchedWords++;
      }
    }

    if (matchedWords > 0) {
      const confidence = matchedWords / titleWords.length;
      if (confidence >= 0.6) {
        return { type: "title_substring", confidence: confidence * 0.8 };
      }
    }

    return null;
  }

  /**
   * Calculate maximum prefix match between two import paths
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

    // If no exact suffix match, try exact filename match
    if (maxPrefixLength === 0) {
      const fileName = filePathParts[filePathParts.length - 1];
      const bibFileName = bibPathParts[bibPathParts.length - 1];

      if (fileName && bibFileName) {
        // Remove .pdf extension for comparison
        const cleanFileName = fileName.replace(/\.pdf$/i, "");
        const cleanBibFileName = bibFileName.replace(/\.pdf$/i, "");

        // Check for exact filename match
        if (cleanFileName === cleanBibFileName) {
          return {
            prefixLength: 1,
            confidence: 0.8, // Lower confidence for filename-only matches
            type: "filename_similarity",
          };
        }

        // Check for similar filenames (e.g., with version suffixes)
        if (cleanFileName.includes(cleanBibFileName) || cleanBibFileName.includes(cleanFileName)) {
          return {
            prefixLength: 1,
            confidence: 0.7, // Even lower confidence for similar filenames
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

  private normalizePath(path: string): string {
    if (!path) return "";

    return path.toLowerCase().replace(/\\/g, "/").replace(/\/+/g, "/").replace(/^\/*/, "").replace(/\/*$/, "").trim();
  }
}
