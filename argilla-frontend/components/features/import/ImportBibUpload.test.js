import { mount } from "@vue/test-utils";
import ImportBibUpload from "./ImportBibUpload.vue";

// Mock the bibtex-parse-js library
jest.mock("bibtex-parse-js", () => ({
  toJSON: jest.fn(),
}));

const bibtexParse = require("bibtex-parse-js");

describe("ImportBibUpload", () => {
  let wrapper;

  beforeEach(() => {
    wrapper = mount(ImportBibUpload, {
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

  describe("Component Structure", () => {
    it("should render the component with correct title", () => {
      expect(wrapper.find(".import-bib-upload__title").text()).toBe("Upload Bibliography File");
    });

    it("should show supported formats section", () => {
      expect(wrapper.find(".import-bib-upload__formats-title").text()).toBe("Supported Export Sources");
      expect(wrapper.text()).toContain("Zotero (.bib export)");
      expect(wrapper.text()).toContain("EndNote (.bib export)");
      expect(wrapper.text()).toContain("Mendeley (.bib export)");
    });

    it("should have dropzone with correct initial state", () => {
      const dropzone = wrapper.find(".import-bib-upload__dropzone");
      expect(dropzone.exists()).toBe(true);
      expect(dropzone.text()).toContain("Drop your .bib file here or click to browse");
    });
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
      },
    };

    it("should parse BibTeX content successfully", async () => {
      bibtexParse.toJSON.mockReturnValue([mockBibTexEntry]);

      const bibTexContent = `@article{test2024,
        title = {Test Article Title},
        author = {John Doe and Jane Smith},
        year = {2024}
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

    it("should emit update event on successful parsing", async () => {
      bibtexParse.toJSON.mockReturnValue([mockBibTexEntry]);

      await wrapper.vm.parseBibTexContent("mock content");
      wrapper.vm.fileName = "test.bib";
      wrapper.vm.isFileUploaded = true;

      wrapper.vm.emitUpdate();

      expect(wrapper.emitted("update")).toBeTruthy();
      expect(wrapper.emitted("update")[0][0]).toMatchObject({
        isValid: true,
        fileName: "test.bib",
        parsedEntries: expect.any(Array),
        dataframeData: expect.any(Object),
        rawContent: expect.any(String),
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
  });

  describe("File Handling", () => {
    it("should validate file types correctly", () => {
      const validBibFile = new File(["content"], "test.bib", { type: "text/plain" });
      const validBibtexFile = new File(["content"], "test.bibtex", { type: "text/plain" });
      const invalidFile = new File(["content"], "test.pdf", { type: "application/pdf" });

      expect(wrapper.vm.isValidFileType(validBibFile)).toBe(true);
      expect(wrapper.vm.isValidFileType(validBibtexFile)).toBe(true);
      expect(wrapper.vm.isValidFileType(invalidFile)).toBe(false);
    });

    it("should process file and emit update", async () => {
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

      expect(wrapper.emitted("update")).toBeTruthy();
      expect(wrapper.vm.isFileUploaded).toBe(true);
      expect(wrapper.vm.fileName).toBe("test.bib");
    });
  });

  describe("Error Handling", () => {
    it("should show error for invalid file type", async () => {
      const invalidFile = new File(["content"], "test.pdf", { type: "application/pdf" });

      await wrapper.vm.processFile(invalidFile);

      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.errorMessage).toContain("Invalid file type");
      expect(wrapper.emitted("update")).toBeTruthy();
      expect(wrapper.emitted("update")[0][0].isValid).toBe(false);
    });

    it("should show error for empty BibTeX file", async () => {
      bibtexParse.toJSON.mockReturnValue([]);

      const file = new File([""], "empty.bib");
      jest.spyOn(wrapper.vm, "readFileContent").mockResolvedValue("");

      await wrapper.vm.processFile(file);

      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.errorMessage).toContain("No valid BibTeX entries found");
    });

    it("should display error in UI", async () => {
      wrapper.vm.showError("Test error message");

      await wrapper.vm.$nextTick();

      expect(wrapper.find(".import-bib-upload__error").exists()).toBe(true);
      expect(wrapper.find(".import-bib-upload__error").text()).toContain("Test error message");
    });
  });

  describe("Computed Properties", () => {
    it("should return correct dropzone icon", () => {
      expect(wrapper.vm.getDropzoneIcon).toBe("import");

      wrapper.vm.hasError = true;
      expect(wrapper.vm.getDropzoneIcon).toBe("danger");

      wrapper.vm.hasError = false;
      wrapper.vm.isFileUploaded = true;
      expect(wrapper.vm.getDropzoneIcon).toBe("check");
    });

    it("should return correct dropzone text", () => {
      expect(wrapper.vm.getDropzoneText).toBe("Drop your .bib file here or click to browse");

      wrapper.vm.hasError = true;
      expect(wrapper.vm.getDropzoneText).toBe("Error parsing file");

      wrapper.vm.hasError = false;
      wrapper.vm.isFileUploaded = true;
      wrapper.vm.fileName = "test.bib";
      expect(wrapper.vm.getDropzoneText).toBe("test.bib uploaded successfully");
    });

    it("should calculate isValid correctly", () => {
      expect(wrapper.vm.isValid).toBe(false);

      wrapper.vm.isFileUploaded = true;
      wrapper.vm.parsedEntries = [{ reference: "test" }];
      expect(wrapper.vm.isValid).toBe(true);

      wrapper.vm.hasError = true;
      expect(wrapper.vm.isValid).toBe(false);
    });

    it("should detect fields correctly", async () => {
      wrapper.vm.parsedEntries = [
        { reference: "test1", title: "Title 1", year: "2024" },
        { reference: "test2", title: "Title 2", authors: "Author" },
      ];

      expect(wrapper.vm.detectedFields).toEqual(["authors", "reference", "title", "year"]);
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

    it("should reset component state and emit update", () => {
      wrapper.vm.isFileUploaded = true;
      wrapper.vm.hasError = true;
      wrapper.vm.parsedEntries = [{ test: "data" }];

      wrapper.vm.reset();

      expect(wrapper.vm.isFileUploaded).toBe(false);
      expect(wrapper.vm.hasError).toBe(false);
      expect(wrapper.vm.parsedEntries).toEqual([]);
      expect(wrapper.emitted("update")).toBeTruthy();
    });
  });

  describe("Preview Display", () => {
    beforeEach(async () => {
      wrapper.vm.parsedEntries = Array.from({ length: 10 }, (_, i) => ({
        reference: `test${i}`,
        title: `Title ${i}`,
        authors: `Author ${i}`,
        year: "2024",
        type: "article",
        doi: `10.1000/test.${i}`,
      }));
      wrapper.vm.isFileUploaded = true;
      await wrapper.vm.$nextTick();
    });

    it("should show preview section when file is uploaded", () => {
      expect(wrapper.find(".import-bib-upload__preview").exists()).toBe(true);
      expect(wrapper.find(".import-bib-upload__preview-title").text()).toBe("Preview");
    });

    it("should display stats correctly", () => {
      const stats = wrapper.findAll(".import-bib-upload__stat");
      expect(stats.at(0).text()).toContain("Total References:");
      expect(stats.at(0).text()).toContain("10");
      expect(stats.at(1).text()).toContain("Fields Detected:");
    });

    it("should limit preview entries to 5 by default", () => {
      const rows = wrapper.findAll(".import-bib-upload__table tbody tr");
      expect(rows).toHaveLength(5);
    });

    it("should show all entries when showAllEntries is true", async () => {
      wrapper.vm.showAllEntries = true;
      await wrapper.vm.$nextTick();

      const rows = wrapper.findAll(".import-bib-upload__table tbody tr");
      expect(rows).toHaveLength(10);
    });

    it("should show 'Show More' button when there are more than 5 entries", () => {
      expect(wrapper.find(".import-bib-upload__show-more").exists()).toBe(true);
    });
  });
});
