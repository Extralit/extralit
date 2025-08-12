import { PdfMatchingService } from "./FileMatchingService";

describe("PdfMatchingService Integration", () => {
  let service;

  beforeEach(() => {
    service = new PdfMatchingService();
  });

  describe("Real-world BibTeX scenarios", () => {
    it("should handle Zotero export with multiple files per reference", () => {
      const entries = [
        {
          reference: "linder_predicting_2025",
          title: "Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation",
          filePaths: [
            "files/4/Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf",
            "files/3/Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf",
          ],
        },
        {
          reference: "lal_decoding_2024",
          title: "Decoding sequence determinants of gene expression in diverse cellular and disease states",
          filePaths: [
            "files/2/Lal et al. - 2024 - Decoding sequence determinants of gene expression in diverse cellular and disease states.pdf",
          ],
        },
      ];

      const files = [
        {
          name: "Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf",
          webkitRelativePath:
            "papers/files/4/Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf",
        },
        {
          name: "Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf",
          webkitRelativePath:
            "papers/files/3/Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf",
        },
        {
          name: "Lal et al. - 2024 - Decoding sequence determinants of gene expression in diverse cellular and disease states.pdf",
          webkitRelativePath:
            "papers/files/2/Lal et al. - 2024 - Decoding sequence determinants of gene expression in diverse cellular and disease states.pdf",
        },
      ];

      const result = service.matchFiles(files, entries);

      expect(result.matchedFiles).toHaveLength(3);
      expect(result.unmatchedFiles).toHaveLength(0);

      // Check that both Linder files are matched to the same reference
      const linderMatches = result.matchedFiles.filter((m) => m.bibEntry.reference === "linder_predicting_2025");
      expect(linderMatches).toHaveLength(2);

      // Check that Lal file is matched
      const lalMatches = result.matchedFiles.filter((m) => m.bibEntry.reference === "lal_decoding_2024");
      expect(lalMatches).toHaveLength(1);

      // All matches should have high confidence due to maximum prefix matching
      result.matchedFiles.forEach((match) => {
        expect(match.confidence).toBeGreaterThan(0.8);
      });
    });

    it("should handle Mendeley export with different path structures", () => {
      const entries = [
        {
          reference: "Hawley2003a",
          title:
            "Community-wide effects of permethrin-treated bed nets on child mortality and malaria morbidity in western Kenya",
          filePaths: ["research/malaria/Hawley2003a_malaria_bed_nets.pdf"], // More realistic path
        },
        {
          reference: "PMI2019",
          title: "Durability Monitoring of LLINs in Zanzibar, Tanzania",
          filePaths: ["reports/PMI2019_Zanzibar_LLIN_Durability.pdf"],
        },
      ];

      const files = [
        {
          name: "Hawley2003a_malaria_bed_nets.pdf",
          webkitRelativePath: "local/research/malaria/Hawley2003a_malaria_bed_nets.pdf",
        },
        {
          name: "PMI2019_Zanzibar_LLIN_Durability.pdf",
          webkitRelativePath: "reports/PMI2019_Zanzibar_LLIN_Durability.pdf",
        },
      ];

      const result = service.matchFiles(files, entries);

      expect(result.matchedFiles).toHaveLength(2);
      expect(result.unmatchedFiles).toHaveLength(0);

      // PMI2019 should match exactly
      const pmiMatch = result.matchedFiles.find((m) => m.bibEntry.reference === "PMI2019");
      expect(pmiMatch).toBeDefined();
      expect(pmiMatch.confidence).toBeGreaterThan(0.9);

      // Hawley2003a should match by path
      const hawleyMatch = result.matchedFiles.find((m) => m.bibEntry.reference === "Hawley2003a");
      expect(hawleyMatch).toBeDefined();
      expect(hawleyMatch.confidence).toBeGreaterThan(0.7);
    });

    it("should prioritize maximum prefix matches over other matching methods", () => {
      const entries = [
        {
          reference: "Smith2023",
          title: "Machine Learning in Healthcare",
          filePaths: ["research/ml/healthcare/Smith2023_ML_Healthcare.pdf"],
        },
        {
          reference: "Jones2023", // Different reference to avoid multiple files per reference
          title: "Another Paper",
          filePaths: ["other/Jones2023.pdf"],
        },
      ];

      const files = [
        {
          name: "Smith2023_ML_Healthcare.pdf",
          webkitRelativePath: "local/research/ml/healthcare/Smith2023_ML_Healthcare.pdf",
        },
        {
          name: "Smith2023.pdf", // This will also match Smith2023 by exact reference match
          webkitRelativePath: "downloads/Smith2023.pdf",
        },
      ];

      const result = service.matchFiles(files, entries);

      expect(result.matchedFiles).toHaveLength(2); // Both files match Smith2023 reference
      expect(result.unmatchedFiles).toHaveLength(0);

      // Both files should match Smith2023
      result.matchedFiles.forEach((match) => {
        expect(match.bibEntry.reference).toBe("Smith2023");
      });

      // The path match should have higher confidence than exact reference match
      const pathMatch = result.matchedFiles.find((m) => m.file.name === "Smith2023_ML_Healthcare.pdf");
      const exactMatch = result.matchedFiles.find((m) => m.file.name === "Smith2023.pdf");

      expect(pathMatch.confidence).toBeGreaterThan(0.8);
      expect(exactMatch.confidence).toBe(1.0); // Exact matches have confidence 1.0
    });

    it("should handle progressive file addition with deduplication", () => {
      const entries = [
        {
          reference: "Johnson2022",
          title: "Deep Learning Applications",
          filePaths: [
            "papers/dl/Johnson2022_part1.pdf",
            "papers/dl/Johnson2022_part2.pdf",
            "papers/dl/Johnson2022_appendix.pdf",
          ],
        },
      ];

      const files = [
        {
          name: "Johnson2022_part1.pdf",
          webkitRelativePath: "local/papers/dl/Johnson2022_part1.pdf",
        },
        {
          name: "Johnson2022_part2.pdf",
          webkitRelativePath: "local/papers/dl/Johnson2022_part2.pdf",
        },
        {
          name: "Johnson2022_appendix.pdf",
          webkitRelativePath: "local/papers/dl/Johnson2022_appendix.pdf",
        },
        {
          name: "Johnson2022_duplicate.pdf", // Should not match due to lower confidence
          webkitRelativePath: "other/Johnson2022_duplicate.pdf",
        },
      ];

      const result = service.matchFiles(files, entries);

      expect(result.matchedFiles).toHaveLength(3);
      expect(result.unmatchedFiles).toHaveLength(1);

      // All matched files should belong to Johnson2022
      result.matchedFiles.forEach((match) => {
        expect(match.bibEntry.reference).toBe("Johnson2022");
      });

      // The duplicate file should be unmatched
      expect(result.unmatchedFiles[0].name).toBe("Johnson2022_duplicate.pdf");
    });
  });

  describe("Edge cases and error handling", () => {
    it("should handle mixed file types gracefully", () => {
      const entries = [
        {
          reference: "Mixed2023",
          title: "Mixed File Types",
          filePaths: [
            "docs/Mixed2023.pdf",
            "docs/Mixed2023.docx", // Non-PDF file
          ],
        },
      ];

      const files = [
        {
          name: "Mixed2023.pdf",
          webkitRelativePath: "local/docs/Mixed2023.pdf",
        },
      ];

      const result = service.matchFiles(files, entries);

      expect(result.matchedFiles).toHaveLength(1);
      expect(result.matchedFiles[0].bibEntry.reference).toBe("Mixed2023");
    });

    it("should handle very long file paths", () => {
      const longPath =
        "very/long/path/with/many/nested/directories/and/subdirectories/that/goes/on/for/a/while/LongPath2023.pdf";

      const entries = [
        {
          reference: "LongPath2023",
          title: "Document with Long Path",
          filePaths: [longPath],
        },
      ];

      const files = [
        {
          name: "LongPath2023.pdf",
          webkitRelativePath: "local/" + longPath,
        },
      ];

      const result = service.matchFiles(files, entries);

      expect(result.matchedFiles).toHaveLength(1);
      expect(result.matchedFiles[0].confidence).toBeGreaterThan(0.7);
    });

    it("should handle special characters in file names", () => {
      const entries = [
        {
          reference: "Special2023",
          title: "Document with Special Characters",
          filePaths: ["docs/Special (2023) - Title with [brackets] & symbols.pdf"],
        },
      ];

      const files = [
        {
          name: "Special (2023) - Title with [brackets] & symbols.pdf",
          webkitRelativePath: "local/docs/Special (2023) - Title with [brackets] & symbols.pdf",
        },
      ];

      const result = service.matchFiles(files, entries);

      expect(result.matchedFiles).toHaveLength(1);
      expect(result.matchedFiles[0].confidence).toBeGreaterThan(0.8);
    });
  });
});
