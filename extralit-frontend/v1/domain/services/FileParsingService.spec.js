import { FileParsingService, BibTeXParser, CSVParser, DataframeBuilder } from "./FileParsingService";

describe("FileService", () => {
  let fileService;

  beforeEach(() => {
    fileService = new FileParsingService();
  });

  describe("BibTeXParser", () => {
    let parser;

    beforeEach(() => {
      parser = new BibTeXParser();
    });

    it("should parse valid BibTeX content", () => {
      const content = `
        @article{smith2023,
          title={Machine Learning in Healthcare},
          author={Smith, John and Jones, Alice},
          year={2023},
          journal={Nature Medicine}
        }
      `;

      const entries = parser.parse(content);

      expect(entries).toHaveLength(1);
      expect(entries[0]).toMatchObject({
        reference: "smith2023",
        type: "article",
        title: "Machine Learning in Healthcare",
        authors: "Smith, John;Jones, Alice",
        year: "2023",
        journal: "Nature Medicine",
      });
    });

    it("should handle empty BibTeX content", () => {
      expect(() => parser.parse("")).toThrow("No valid BibTeX entries found");
    });

    it("should clean BibTeX fields properly", () => {
      const content = `
        @article{test2023,
          title={{Machine Learning} in Healthcare},
          author={Smith, John}
        }
      `;

      const entries = parser.parse(content);

      expect(entries[0].title).toBe("Machine Learning in Healthcare");
    });
  });

  describe("CSVParser", () => {
    let parser;

    beforeEach(() => {
      parser = new CSVParser();
    });

    it("should parse valid CSV content", () => {
      const content = "reference,title,year\nsmith2023,Machine Learning,2023\njones2022,Deep Learning,2022";

      const result = parser.parse(content);

      expect(result.columns).toEqual(["reference", "title", "year"]);
      expect(result.data).toHaveLength(2);
      expect(result.data[0]).toMatchObject({
        reference: "smith2023",
        title: "Machine Learning",
        year: "2023",
      });
    });

    it("should process CSV with config", () => {
      const rawData = [
        { ref: "smith2023", title: "ML Paper", files: "paper1.pdf" },
        { ref: "jones2022", title: "DL Paper", files: "paper2.pdf;supplement.pdf" },
      ];

      const config = {
        referenceColumn: "ref",
        filesColumn: "files",
      };

      const entries = parser.processWithConfig(rawData, config);

      expect(entries).toHaveLength(2);
      expect(entries[0]).toMatchObject({
        reference: "smith2023",
        type: "csv_entry",
        title: "ML Paper",
        filePaths: ["paper1.pdf"],
      });
      expect(entries[1].filePaths).toEqual(["paper2.pdf", "supplement.pdf"]);
    });

    it("should handle missing reference column", () => {
      const rawData = [{ title: "Test" }];
      const config = { referenceColumn: "ref" };

      expect(() => parser.processWithConfig(rawData, config)).toThrow(
        'No data found in the selected reference column "ref".'
      );
    });
  });

  describe("DataframeBuilder", () => {
    it("should build dataframe from entries", () => {
      const entries = [
        { reference: "smith2023", type: "article", year: "2023" },
        { reference: "jones2022", type: "article", year: "2022" },
      ];

      const dataframe = DataframeBuilder.build(entries);

      expect(dataframe.schema.primaryKey).toEqual(["reference"]);
      expect(dataframe.schema.fields).toEqual(
        expect.arrayContaining([
          { name: "reference", type: "string" },
          { name: "type", type: "string" },
          { name: "year", type: "integer" },
        ])
      );
      expect(dataframe.data).toEqual(entries);
    });

    it("should handle empty entries", () => {
      const dataframe = DataframeBuilder.build([]);

      expect(dataframe.schema.fields).toEqual([]);
      expect(dataframe.data).toEqual([]);
    });
  });

  describe("FileService integration", () => {
    it("should validate file types correctly", () => {
      const csvFile = { name: "test.csv" };
      const bibFile = { name: "test.bib" };
      const invalidFile = { name: "test.txt" };

      expect(fileService.isValidFileType(csvFile, [".csv", ".bib"])).toBe(true);
      expect(fileService.isValidFileType(bibFile, [".csv", ".bib"])).toBe(true);
      expect(fileService.isValidFileType(invalidFile, [".csv", ".bib"])).toBe(false);
    });
  });
});
