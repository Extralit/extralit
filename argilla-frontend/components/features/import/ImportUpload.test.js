import { mount } from "@vue/test-utils";
import ImportUpload from "./ImportUpload.vue";

// Mock the bibtex-parse-js library
jest.mock("bibtex-parse-js", () => ({
  toJSON: jest.fn(),
}));

const bibtexParse = require("bibtex-parse-js");

describe("ImportUpload", () => {
  let wrapper;

  beforeEach(() => {
    wrapper = mount(ImportUpload, {
      stubs: {
        "base-icon": true,
        "base-button": true,
      },
    });
  });

  afterEach(() => {
    wrapper.destroy();
    jest.clearAllMocks();
  });

  describe("BibTeX Parsing", () => {
    const mockBibTexEntry = {
      citationKey: "test2024",
      entryType: "article",
      entryTags: {
        title: "Test Article Title",
        author: "John Doe and Jane Smith",
        year: "2024",
        journal: "Test Journal",
        doi: "10.1000/test.2024",
        pmid: "12345678",
        abstract: "This is a test abstract",
        keywords: "test, bibtex, parsing",
      },
    };

    it("should parse BibTeX content successfully", async () => {
      bibtexParse.toJSON.mockReturnValue([mockBibTexEntry]);

      const bibTexContent = `@article{test2024,
        title = {Test Article Title},
        author = {John Doe and Jane Smith},
        year = {2024},
        journal = {Test Journal},
        doi = {10.1000/test.2024}
      }`;

      await wrapper.vm.parseBibTexContent(bibTexContent);

      expect(wrapper.vm.parsedEntries).toHaveLength(1);
      expect(wrapper.vm.parsedEntries[0]).toMatchObject({
        reference: "test2024",
        type: "article",
        title: "Test Article Title",
        authors: "John Doe, Jane Smith",
        year: "2024",
        doi: "10.1000/test.2024",
      });
    });

    it("should create generic dataframe format", async () => {
      bibtexParse.toJSON.mockReturnValue([mockBibTexEntry]);

      await wrapper.vm.parseBibTexContent("mock content");

      expect(wrapper.vm.dataframeData).toBeDefined();
      expect(wrapper.vm.dataframeData.schema).toBeDefined();
      expect(wrapper.vm.dataframeData.schema.primaryKey).toEqual(["reference"]);
      expect(wrapper.vm.dataframeData.data).toHaveLength(1);
      expect(wrapper.vm.dataframeData.data[0].reference).toBe("test2024");
    });

    it("should handle malformed BibTeX entries gracefully", async () => {
      const malformedEntry = {
        // Missing citationKey
        entryType: "article",
        entryTags: { title: "Test" },
      };

      bibtexParse.toJSON.mockReturnValue([mockBibTexEntry, malformedEntry]);

      await wrapper.vm.parseBibTexContent("mock content");

      // Should still process the valid entry
      expect(wrapper.vm.parsedEntries).toHaveLength(1);
      expect(wrapper.vm.parseErrors).toHaveLength(1);
      expect(wrapper.vm.parseErrors[0]).toContain("Missing citation key");
    });

    it("should extract authors correctly", () => {
      expect(wrapper.vm.extractAuthors("John Doe and Jane Smith")).toBe("John Doe, Jane Smith");
      expect(wrapper.vm.extractAuthors("Smith, John and Doe, Jane")).toBe("Smith, John, Doe, Jane");
      expect(wrapper.vm.extractAuthors("")).toBeNull();
      expect(wrapper.vm.extractAuthors(null)).toBeNull();
    });

    it("should extract year correctly", () => {
      expect(wrapper.vm.extractYear("2024")).toBe("2024");
      expect(wrapper.vm.extractYear("2024-01-01")).toBe("2024");
      expect(wrapper.vm.extractYear("January 2024")).toBe("2024");
      expect(wrapper.vm.extractYear("invalid")).toBeNull();
    });

    it("should clean BibTeX fields correctly", () => {
      expect(wrapper.vm.cleanBibTexField("{Test Title}")).toBe("Test Title");
      expect(wrapper.vm.cleanBibTexField("{{Nested Braces}}")).toBe("Nested Braces");
      expect(wrapper.vm.cleanBibTexField('"Quoted Text"')).toBe("Quoted Text");
      expect(wrapper.vm.cleanBibTexField("  Trimmed  ")).toBe("Trimmed");
      expect(wrapper.vm.cleanBibTexField("")).toBeNull();
      expect(wrapper.vm.cleanBibTexField(null)).toBeNull();
    });

    it("should infer field types correctly", () => {
      const entries = [
        { year: "2024", volume: "10", title: "Test" },
        { year: "2023", volume: "11", title: "Another" },
      ];

      expect(wrapper.vm.inferFieldType(entries, "year")).toBe("integer");
      expect(wrapper.vm.inferFieldType(entries, "volume")).toBe("integer");
      expect(wrapper.vm.inferFieldType(entries, "title")).toBe("string");
    });
  });

  describe("File Handling", () => {
    it("should validate file types correctly", () => {
      const validFile = new File(["content"], "test.bib", { type: "text/plain" });
      const invalidFile = new File(["content"], "test.pdf", { type: "application/pdf" });

      expect(wrapper.vm.isValidFileType(validFile)).toBe(true);
      expect(wrapper.vm.isValidFileType(invalidFile)).toBe(false);
    });

    it("should emit file-parsed event on successful parsing", async () => {
      bibtexParse.toJSON.mockReturnValue([
        {
          citationKey: "test2024",
          entryType: "article",
          entryTags: { title: "Test" },
        },
      ]);

      const file = new File(["@article{test2024, title={Test}}"], "test.bib");

      // Mock file reading
      jest.spyOn(wrapper.vm, "readFileContent").mockResolvedValue("@article{test2024, title={Test}}");

      await wrapper.vm.processFile(file);

      expect(wrapper.emitted("file-parsed")).toBeTruthy();
      expect(wrapper.emitted("file-parsed")[0][0]).toMatchObject({
        fileName: "test.bib",
        parsedEntries: expect.any(Array),
        dataframeData: expect.any(Object),
        rawContent: expect.any(String),
      });
    });
  });

  describe("Error Handling", () => {
    it("should show error for invalid file type", async () => {
      const invalidFile = new File(["content"], "test.pdf", { type: "application/pdf" });

      await wrapper.vm.processFile(invalidFile);

      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.errorMessage).toContain("Invalid file type");
    });

    it("should show error for empty BibTeX file", async () => {
      bibtexParse.toJSON.mockReturnValue([]);

      const file = new File([""], "empty.bib");
      jest.spyOn(wrapper.vm, "readFileContent").mockResolvedValue("");

      await wrapper.vm.processFile(file);

      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.errorMessage).toContain("No valid BibTeX entries found");
    });

    it("should handle parsing exceptions", async () => {
      bibtexParse.toJSON.mockImplementation(() => {
        throw new Error("Parse error");
      });

      const file = new File(["invalid"], "test.bib");
      jest.spyOn(wrapper.vm, "readFileContent").mockResolvedValue("invalid");

      await wrapper.vm.processFile(file);

      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.errorMessage).toContain("BibTeX parsing failed");
    });
  });

  describe("Public Methods", () => {
    it("should return parsed data via getParsedData", async () => {
      bibtexParse.toJSON.mockReturnValue([
        {
          citationKey: "test2024",
          entryType: "article",
          entryTags: { title: "Test" },
        },
      ]);

      await wrapper.vm.parseBibTexContent("mock content");
      wrapper.vm.fileName = "test.bib";
      wrapper.vm.rawBibTexContent = "mock content";

      const data = wrapper.vm.getParsedData();

      expect(data).toMatchObject({
        fileName: "test.bib",
        parsedEntries: expect.any(Array),
        dataframeData: expect.any(Object),
        rawContent: "mock content",
      });
    });

    it("should reset component state", () => {
      wrapper.vm.isFileUploaded = true;
      wrapper.vm.hasError = true;
      wrapper.vm.parsedEntries = [{ test: "data" }];

      wrapper.vm.reset();

      expect(wrapper.vm.isFileUploaded).toBe(false);
      expect(wrapper.vm.hasError).toBe(false);
      expect(wrapper.vm.parsedEntries).toEqual([]);
    });
  });

  describe("Computed Properties", () => {
    it("should detect fields correctly", async () => {
      wrapper.vm.parsedEntries = [
        { reference: "test1", title: "Title 1", year: "2024" },
        { reference: "test2", title: "Title 2", author: "Author" },
      ];

      expect(wrapper.vm.detectedFields).toEqual(["author", "reference", "title", "year"]);
    });

    it("should limit preview entries", () => {
      wrapper.vm.parsedEntries = Array.from({ length: 10 }, (_, i) => ({ reference: `test${i}` }));

      expect(wrapper.vm.previewEntries).toHaveLength(5);

      wrapper.vm.showAllEntries = true;
      expect(wrapper.vm.previewEntries).toHaveLength(10);
    });
  });
});
