import bibtexParse from "@orcid/bibtex-parse-js";
import Papa from "papaparse";
import { TableData } from "../entities/table/TableData";
import { DataFrameSchema } from "../entities/table/Schema";
import type { IFileService, ParsedEntry, ParseResult, CSVConfig, CSVPreviewData } from "./IFileService";
import type { FieldType } from "~/v1/domain/entities/import/ImportAnalysis";

export class BibTeXParser {
  parse(content: string): ParsedEntry[] {
    const parsed = bibtexParse.toJSON(content);

    if (!Array.isArray(parsed) || parsed.length === 0) {
      throw new Error("No valid BibTeX entries found");
    }

    const entries: ParsedEntry[] = [];

    parsed.forEach((entry, index) => {
      try {
        const processedEntry = this.processEntry(entry);
        if (processedEntry) {
          entries.push(processedEntry);
        }
      } catch (error) {
        console.warn(`BibTeX entry ${index + 1}: ${error.message}`);
      }
    });

    return entries;
  }

  private processEntry(entry: any): ParsedEntry | null {
    if (!entry.citationKey) {
      throw new Error("Missing citation key (reference)");
    }

    const processedEntry: ParsedEntry = {
      reference: entry.citationKey,
      type: entry.entryType || "unknown",
    };

    if (entry.entryTags) {
      Object.keys(entry.entryTags).forEach((key) => {
        const rawValue = entry.entryTags[key];
        const processedValue = this.cleanField(rawValue);

        switch (key.toLowerCase()) {
          case "author":
            processedEntry.authors = this.extractAuthors(rawValue);
            break;
          case "year":
            processedEntry.year = this.extractYear(rawValue);
            break;
          case "date":
            if (!processedEntry.year) {
              processedEntry.year = this.extractYear(rawValue);
            }
            break;
          case "file":
            processedEntry.filePaths = this.parseFilePaths(rawValue);
            break;
          default:
            processedEntry[key] = processedValue;
            break;
        }
      });
    }

    return processedEntry;
  }

  private cleanField(field: string | null): string | null {
    if (!field) return null;

    const cleaned = field
      .toString()
      .replace(/[\{\}]/g, "")
      .replace(/^"+|"+$/g, "")
      .trim();

    return cleaned || null;
  }

  private extractAuthors(authorField: string): string | null {
    if (!authorField) return null;

    const cleaned = this.cleanField(authorField);
    if (!cleaned) return null;

    const authors = cleaned
      .split(/\s+and\s+/i)
      .map((author) => author.trim())
      .filter((author) => author.length > 0);

    return authors.length > 0 ? authors.join(";") : null;
  }

  private extractYear(yearField: string): string | null {
    if (!yearField) return null;

    const cleaned = this.cleanField(yearField);
    if (!cleaned) return null;

    const yearMatch = cleaned.match(/\b(19|20)\d{2}\b/);
    return yearMatch ? yearMatch[0] : null;
  }

  private parseFilePaths(fileField: string): string[] {
    if (!fileField) return [];

    const cleaned = this.cleanField(fileField);
    if (!cleaned) return [];

    const filePaths: string[] = [];
    const fileEntries = cleaned
      .split(";")
      .map((f) => f.trim())
      .filter((f) => f.length > 0);

    for (const fileEntry of fileEntries) {
      const parts = fileEntry.split(":");
      if (parts.length >= 2) {
        const filePath = parts[1].trim();
        if (filePath && filePath !== "") {
          filePaths.push(filePath);
        }
      }
    }

    return filePaths;
  }
}

export class CSVParser {
  parse(content: string): { data: Record<string, any>[]; columns: string[] } {
    const parseResult = Papa.parse(content, {
      header: true,
      skipEmptyLines: true,
      transformHeader: (header) => header.trim(),
      transform: (value) => value.trim(),
    });

    if (parseResult.errors && parseResult.errors.length > 0) {
      const errorMessages = parseResult.errors.map((error) => `Row ${error.row}: ${error.message}`).join("\n");
      throw new Error(`CSV parsing errors:\n${errorMessages}`);
    }

    if (!parseResult.data || parseResult.data.length === 0) {
      throw new Error("No data found in CSV file");
    }

    const columns = parseResult.meta.fields || [];
    if (columns.length === 0) {
      throw new Error("No columns found in CSV file. Please ensure the file has a header row.");
    }

    return {
      data: parseResult.data,
      columns,
    };
  }

  processWithConfig(rawData: Record<string, any>[], config: CSVConfig): ParsedEntry[] {
    if (!config.referenceColumn) {
      throw new Error("Reference column is required");
    }

    const referencesWithData = rawData.filter(
      (row) => row[config.referenceColumn] && row[config.referenceColumn].trim() !== ""
    );

    if (referencesWithData.length === 0) {
      throw new Error(`No data found in the selected reference column "${config.referenceColumn}".`);
    }

    const entries: ParsedEntry[] = [];

    referencesWithData.forEach((row, index) => {
      try {
        const processedEntry = this.processEntry(row, config);
        if (processedEntry) {
          entries.push(processedEntry);
        }
      } catch (error) {
        console.warn(`CSV row ${index + 1}: ${error.message}`);
      }
    });

    return entries;
  }

  private processEntry(row: Record<string, any>, config: CSVConfig): ParsedEntry | null {
    const reference = row[config.referenceColumn]?.trim();
    if (!reference) {
      throw new Error("Missing reference value");
    }

    const processedEntry: ParsedEntry = {
      reference,
      type: "csv_entry",
    };

    Object.keys(row).forEach((column) => {
      const value = row[column]?.trim();
      if (value && column !== config.referenceColumn) {
        if (column === config.filesColumn) {
          processedEntry.filePaths = this.parseFilePaths(value);
        } else {
          const cleanColumnName = this.cleanColumnName(column);
          processedEntry[cleanColumnName] = value;
        }
      }
    });

    return processedEntry;
  }

  private parseFilePaths(fileValue: string): string[] {
    if (!fileValue) return [];

    const separators = [";", ",", "|", "\n"];
    let filePaths = [fileValue];

    for (const separator of separators) {
      if (fileValue.includes(separator)) {
        filePaths = fileValue
          .split(separator)
          .map((path) => path.trim())
          .filter((path) => path.length > 0);
        break;
      }
    }

    return filePaths;
  }

  private cleanColumnName(columnName: string): string {
    return columnName
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "");
  }
}

export class DataframeBuilder {
  static build(entries: ParsedEntry[]): TableData {
    if (entries.length === 0) {
      return new TableData([], new DataFrameSchema([], ["reference"]));
    }

    const allFields = new Set<string>();
    entries.forEach((entry) => {
      Object.keys(entry).forEach((field) => allFields.add(field));
    });

    const fields = Array.from(allFields).map((fieldName) => ({
      name: fieldName,
      type: this.inferFieldType(entries, fieldName),
    }));

    return new TableData(entries, new DataFrameSchema(fields, ["reference"]));
  }

  private static inferFieldType(entries: ParsedEntry[], fieldName: string): FieldType {
    const values = entries.map((entry) => entry[fieldName]).filter((value) => value != null && value !== "");

    if (values.length === 0) return "string";

    if (values.every((value) => !isNaN(value) && !isNaN(parseFloat(value)))) {
      return values.every((value) => Number.isInteger(parseFloat(value))) ? "integer" : "float";
    }

    return "string";
  }
}

export class FileService implements IFileService {
  private bibTexParser = new BibTeXParser();
  private csvParser = new CSVParser();

  async parseBibTeX(content: string): Promise<ParseResult> {
    const entries = this.bibTexParser.parse(content);
    const dataframeData = DataframeBuilder.build(entries);

    return {
      entries,
      dataframeData,
    };
  }

  async parseCSVForPreview(content: string): Promise<CSVPreviewData> {
    const { data, columns } = this.csvParser.parse(content);

    return {
      columns,
      previewRows: data.slice(0, 3),
      rawData: data,
    };
  }

  async parseCSVWithConfig(rawData: Record<string, any>[], config: CSVConfig): Promise<ParseResult> {
    const entries = this.csvParser.processWithConfig(rawData, config);
    const dataframeData = DataframeBuilder.build(entries);

    return {
      entries,
      dataframeData,
    };
  }

  async readFileContent(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = () => reject(new Error("Failed to read file"));
      reader.readAsText(file, "utf-8");
    });
  }

  isValidFileType(file: File, validExtensions: string[]): boolean {
    const fileName = file.name.toLowerCase();
    return validExtensions.some((ext) => fileName.endsWith(ext));
  }
}
