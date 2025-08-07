import { PdfMatchingService } from "./PdfMatchingService";

describe("PdfMatchingService", () => {
  let service;
  let mockEntries;
  let mockFiles;

  beforeEach(() => {
    service = new PdfMatchingService();

    // Mock bibliography entries with file paths
    mockEntries = [
      {
        reference: "Smith2023",
        title: "Machine Learning in Healthcare",
        filePaths: ["papers/healthcare/Smith2023_ML_Healthcare.pdf"],
      },
      {
        reference: "Johnson2022",
        title: "Deep Learning Applications",
        filePaths: ["research/dl/Johnson2022_part1.pdf", "research/dl/Johnson2022_part2.pdf"],
      },
      {
        reference: "Brown2021",
        title: "Neural Networks Overview",
        filePaths: ["documents/neural/Brown2021.pdf"],
      },
    ];

    // Mock file objects with webkitRelativePath
    mockFiles = [
      {
        name: "Smith2023_ML_Healthcare.pdf",
        webkitRelativePath: "papers/healthcare/Smith2023_ML_Healthcare.pdf",
      },
      {
        name: "Johnson2022_part1.pdf",
        webkitRelativePath: "research/dl/Johnson2022_part1.pdf",
      },
      {
        name: "Johnson2022_part2.pdf",
        webkitRelativePath: "research/dl/Johnson2022_part2.pdf",
      },
      {
        name: "unmatched_file.pdf",
        webkitRelativePath: "random/folder/unmatched_file.pdf",
      },
    ];
  });

  describe("matchFiles", () => {
    it("should return empty results when no entries or files provided", () => {
      const result = service.matchFiles([], []);
      expect(result.matchedFiles).toEqual([]);
      expect(result.unmatchedFiles).toEqual([]);
    });

    it("should return all files as unmatched when no entries provided", () => {
      const result = service.matchFiles(mockFiles, []);
      expect(result.matchedFiles).toEqual([]);
      expect(result.unmatchedFiles).toEqual(mockFiles);
    });

    it("should match files using maximum prefix path matching", () => {
      const result = service.matchFiles(mockFiles, mockEntries);

      expect(result.matchedFiles).toHaveLength(3);
      expect(result.unmatchedFiles).toHaveLength(1);

      // Check that Smith2023 file is matched
      const smithMatch = result.matchedFiles.find((m) => m.file.name === "Smith2023_ML_Healthcare.pdf");
      expect(smithMatch).toBeDefined();
      expect(smithMatch.bibEntry.reference).toBe("Smith2023");
      expect(smithMatch.confidence).toBeGreaterThan(0.8);

      // Check that both Johnson2022 files are matched to the same reference
      const johnsonMatches = result.matchedFiles.filter((m) => m.bibEntry.reference === "Johnson2022");
      expect(johnsonMatches).toHaveLength(2);

      // Check unmatched file
      expect(result.unmatchedFiles[0].name).toBe("unmatched_file.pdf");
    });

    it("should handle multiple files per reference correctly", () => {
      const result = service.matchFiles(mockFiles, mockEntries);

      // Count files per reference
      const referenceCount = {};
      result.matchedFiles.forEach((match) => {
        const ref = match.bibEntry.reference;
        referenceCount[ref] = (referenceCount[ref] || 0) + 1;
      });

      expect(referenceCount["Johnson2022"]).toBe(2);
      expect(referenceCount["Smith2023"]).toBe(1);
    });

    it("should sort results by confidence and then by reference", () => {
      const result = service.matchFiles(mockFiles, mockEntries);

      // Check that results are sorted by confidence (descending)
      for (let i = 1; i < result.matchedFiles.length; i++) {
        const current = result.matchedFiles[i];
        const previous = result.matchedFiles[i - 1];

        // Either previous has higher confidence, or same confidence with earlier reference
        expect(
          previous.confidence > current.confidence ||
            (Math.abs(previous.confidence - current.confidence) < 0.01 &&
              previous.bibEntry.reference <= current.bibEntry.reference)
        ).toBe(true);
      }
    });
  });

  describe("calculateMaximumPrefixMatch", () => {
    it("should return exact match for identical paths", () => {
      const result = service.calculateMaximumPrefixMatch(
        "papers/healthcare/Smith2023.pdf",
        "papers/healthcare/Smith2023.pdf"
      );

      expect(result.confidence).toBe(1.0);
      expect(result.type).toBe("exact_path_match");
    });

    it("should calculate suffix matches correctly", () => {
      const result = service.calculateMaximumPrefixMatch(
        "local/papers/healthcare/Smith2023.pdf",
        "remote/papers/healthcare/Smith2023.pdf"
      );

      expect(result.prefixLength).toBe(3); // healthcare/Smith2023.pdf
      expect(result.confidence).toBeGreaterThan(0.7);
      expect(result.type).toBe("partial_suffix_match");
    });

    it("should handle filename similarity when no path match", () => {
      const result = service.calculateMaximumPrefixMatch(
        "completely/different/Smith2023_ML_Healthcare.pdf",
        "totally/unrelated/Smith2023_ML_Healthcare_v2.pdf"
      );

      expect(result.prefixLength).toBe(1);
      expect(result.type).toBe("filename_similarity");
      expect(result.confidence).toBeGreaterThan(0.5);
    });

    it("should return no match for completely different paths", () => {
      const result = service.calculateMaximumPrefixMatch("completely/different/path.pdf", "totally/unrelated/file.pdf");

      expect(result.prefixLength).toBe(0);
      expect(result.confidence).toBe(0);
      expect(result.type).toBe("no_match");
    });
  });

  describe("findMaximumPrefixMatches", () => {
    it("should find best matches using progressive file addition", () => {
      const matches = service.findMaximumPrefixMatches(mockFiles, mockEntries);

      expect(matches.length).toBeGreaterThan(0);

      // Each file should be matched at most once
      const matchedFiles = new Set();
      matches.forEach((match) => {
        expect(matchedFiles.has(match.file)).toBe(false);
        matchedFiles.add(match.file);
      });
    });

    it("should allow multiple files per reference with quality threshold", () => {
      const multiFileEntry = {
        reference: "MultiFile2023",
        title: "Multi-part Document",
        filePaths: ["docs/MultiFile2023_part1.pdf", "docs/MultiFile2023_part2.pdf"],
      };

      const multiFiles = [
        {
          name: "MultiFile2023_part1.pdf",
          webkitRelativePath: "docs/MultiFile2023_part1.pdf",
        },
        {
          name: "MultiFile2023_part2.pdf",
          webkitRelativePath: "docs/MultiFile2023_part2.pdf",
        },
      ];

      const matches = service.findMaximumPrefixMatches(multiFiles, [multiFileEntry]);

      expect(matches.length).toBe(2);
      expect(matches[0].entry.reference).toBe("MultiFile2023");
      expect(matches[1].entry.reference).toBe("MultiFile2023");
    });
  });

  describe("edge cases", () => {
    it("should handle files without webkitRelativePath", () => {
      const filesWithoutWebkit = [{ name: "Smith2023_ML_Healthcare.pdf" }, { name: "Johnson2022_part1.pdf" }];

      const result = service.matchFiles(filesWithoutWebkit, mockEntries);

      // Should still attempt matching using filename
      expect(result.matchedFiles.length).toBeGreaterThan(0);
    });

    it("should handle entries without file paths", () => {
      const entriesWithoutPaths = [
        {
          reference: "NoPath2023",
          title: "Document Without Path",
          filePaths: [],
        },
      ];

      const result = service.matchFiles(mockFiles, entriesWithoutPaths);

      expect(result.matchedFiles).toHaveLength(0);
      expect(result.unmatchedFiles).toEqual(mockFiles);
    });

    it("should handle empty or null file paths gracefully", () => {
      const entriesWithNullPaths = [
        {
          reference: "NullPath2023",
          title: "Document With Null Path",
          filePaths: null,
        },
      ];

      expect(() => {
        service.matchFiles(mockFiles, entriesWithNullPaths);
      }).not.toThrow();
    });
  });
});
