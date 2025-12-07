/**
 * View model for ImportFileUpload component
 * Handles coordination between bibliography and PDF uploads
 */

import { ref, computed, watch, nextTick } from "@nuxtjs/composition-api";
import type { BibliographyData, PdfData } from "./types";
import { TableData } from "~/v1/domain/entities/table/TableData";
import { DataFrameSchema, DataFrameField } from "~/v1/domain/entities/table/Schema";
import { Validators } from "~/v1/domain/entities/table/Validation";

export const useImportFileUploadViewModel = (props: any, { emit }: any) => {
  // Internal flag to prevent recursive updates during initialization
  const isInitializing = ref(false);

  // Bibliography data
  const bibData = ref<BibliographyData>({
    fileName: "",
    dataframeData: null,
    rawContent: "",
  });

  // PDF data
  const pdfData = ref<PdfData>({
    matchedFiles: [],
    unmatchedFiles: [],
    totalFiles: 0,
  });

  // Editable table data for PDF-only uploads
  const editableTableData = ref<any[]>([]);
  const editableTable = ref<any>(null);

  // Computed properties
  const isValid = computed(() => {
    return pdfData.value.totalFiles > 0;
  });

  // Check if we should show the editable table (PDFs uploaded but no bibliography)
  const shouldShowEditableTable = computed(() => {
    const hasPdfs = pdfData.value.totalFiles > 0;
    const noBibliography = !bibData.value.dataframeData || bibData.value.dataframeData.data.length === 0;
    return hasPdfs && noBibliography;
  });

  // Get all PDF file names
  const allPdfFileNames = computed(() => {
    const matched = pdfData.value.matchedFiles.map((mf: any) => mf.file.name);
    const unmatched = pdfData.value.unmatchedFiles.map((f: File) => f.name);
    return [...matched, ...unmatched];
  });

  // Get unmapped PDF files (PDFs not assigned to any reference)
  const unmappedPdfFiles = computed(() => {
    const assignedFiles = new Set<string>();
    
    // Collect all files assigned to references
    editableTableData.value.forEach((row: any) => {
      if (row.files && Array.isArray(row.files)) {
        row.files.forEach((file: string) => assignedFiles.add(file));
      }
    });

    // Return PDFs not in the assigned set
    return allPdfFileNames.value.filter(fileName => !assignedFiles.has(fileName));
  });

  // Configure editable table columns with validators
  const editableTableColumns = computed(() => {
    const pdfFileOptions = allPdfFileNames.value.map(name => ({
      label: name,
      value: name,
    }));

    return [
      {
        field: "reference",
        title: "Reference *",
        frozen: true,
        width: 200,
        editor: "input",
        validator: ["required", "unique"],
      },
      {
        field: "title",
        title: "Title",
        width: 300,
        editor: "input",
      },
      {
        field: "authors",
        title: "Authors",
        width: 200,
        editor: "input",
      },
      {
        field: "year",
        title: "Year",
        width: 100,
        editor: "input",
      },
      {
        field: "journal",
        title: "Journal",
        width: 200,
        editor: "input",
      },
      {
        field: "doi",
        title: "DOI",
        width: 150,
        editor: "input",
      },
      {
        field: "files",
        title: "Files *",
        frozen: true,
        frozenRight: true,
        width: 200,
        editor: "list",
        editorParams: {
          values: pdfFileOptions,
          multiselect: true,
          autocomplete: true,
          listOnEmpty: true,
          clearable: true,
        },
        validator: ["required"],
        formatter: (cell: any) => {
          const value = cell.getValue();
          if (!value || (Array.isArray(value) && value.length === 0)) {
            return '<span style="color: var(--fg-tertiary);">No files</span>';
          }
          const files = Array.isArray(value) ? value : [value];
          const count = files.length;
          return `<span title="${files.join(', ')}">${count} file${count !== 1 ? 's' : ''}</span>`;
        },
      },
    ];
  });

  // Validators for the editable table
  const editableTableValidators = computed<Validators>(() => {
    return {
      reference: [
        { type: "unique", parameters: { column: "reference" } },
        "required",
      ],
      files: ["required"],
    };
  });

  // Event handlers
  const handleBibUpdate = (data: any) => {
    bibData.value = {
      fileName: data.fileName || "",
      dataframeData: data.dataframeData || null,
      rawContent: data.rawContent || "",
    };
    
    // If a bibliography is uploaded, clear the editable table data
    if (data.dataframeData && data.dataframeData.data && data.dataframeData.data.length > 0) {
      editableTableData.value = [];
    }
    
    emitBibUpdate();
  };

  const handlePdfUpdate = (data: any) => {
    pdfData.value = {
      matchedFiles: data.matchedFiles || [],
      unmatchedFiles: data.unmatchedFiles || [],
      totalFiles: data.totalFiles || 0,
    };

    // Initialize editable table if needed (PDFs but no bib)
    if (shouldShowEditableTable.value && editableTableData.value.length === 0) {
      initializeEditableTable();
    }

    // Update dataframe data with matched file paths
    updateDataframeWithFilePaths(data.matchedFiles || []);

    emitPdfUpdate();
  };

  const handleTableCellEdit = (cell: any) => {
    // When a cell is edited, update our data and sync to bibData
    const updatedData = editableTable.value?.getData() || [];
    editableTableData.value = updatedData;
    
    // Convert editable table data to dataframe format
    syncEditableTableToBibData();
  };

  const handleTableBuilt = () => {
    // Table is ready, ensure data is in sync
    if (editableTable.value) {
      const tableData = editableTable.value.getData();
      if (tableData && tableData.length > 0) {
        editableTableData.value = tableData;
      }
    }
  };

  // Event emitters
  const emitBibUpdate = () => {
    emit("bib-update", {
      isValid: true, // table optional, always valid
      fileName: bibData.value.fileName,
      dataframeData: bibData.value.dataframeData,
      rawContent: bibData.value.rawContent,
    });
  };

  const emitPdfUpdate = () => {
    emit("pdf-update", {
      isValid: pdfData.value.totalFiles > 0,
      matchedFiles: pdfData.value.matchedFiles,
      unmatchedFiles: pdfData.value.unmatchedFiles,
      totalFiles: pdfData.value.totalFiles,
    });
  };

  const updateDataframeWithFilePaths = (matchedFiles: any[]) => {
    if (!bibData.value.dataframeData || !matchedFiles.length) {
      return;
    }

    // Ensure the dataframeData has the expected structure
    if (!bibData.value.dataframeData.data || !Array.isArray(bibData.value.dataframeData.data)) {
      console.error('ImportFileUpload: Invalid dataframeData structure', bibData.value.dataframeData);
      return;
    }

    // Create a map of reference to file paths
    const referenceToFiles = new Map<string, string[]>();

    matchedFiles.forEach((matchedFile: any) => {
      const reference = matchedFile.bibEntry?.reference;
      const fileName = matchedFile.file?.name;

      if (reference && fileName) {
        if (!referenceToFiles.has(reference)) {
          referenceToFiles.set(reference, []);
        }
        referenceToFiles.get(reference)!.push(fileName);
      }
    });

    // Update the dataframe data with file paths
    const updatedData = bibData.value.dataframeData.data.map((row: any) => {
      const reference = row.reference || row.key;
      const filePaths = referenceToFiles.get(reference) || [];

      return {
        ...row,
        filePaths
      };
    });

    // Preserve the original structure while updating data
    bibData.value.dataframeData = {
      ...bibData.value.dataframeData,
      data: updatedData
    };

    // Re-emit the bib update with the updated dataframe
    emitBibUpdate();
  };

  // Initialize editable table with empty rows
  const initializeEditableTable = () => {
    // Start with a few empty rows
    const initialRows = Array.from({ length: 3 }, (_, i) => ({
      reference: "",
      title: "",
      authors: "",
      year: "",
      journal: "",
      doi: "",
      files: [],
    }));
    
    editableTableData.value = initialRows;
  };

  // Sync editable table data to bibData format
  const syncEditableTableToBibData = () => {
    if (editableTableData.value.length === 0) {
      return;
    }

    // Filter out empty rows (rows without reference)
    const validRows = editableTableData.value.filter((row: any) => 
      row.reference && row.reference.trim().length > 0
    );

    if (validRows.length === 0) {
      return;
    }

    // Convert to TableData format
    const fields: DataFrameField[] = [
      { name: "reference", type: "string" },
      { name: "title", type: "string" },
      { name: "authors", type: "string" },
      { name: "year", type: "string" },
      { name: "journal", type: "string" },
      { name: "doi", type: "string" },
      { name: "files", type: "string" },
    ];

    const schema = new DataFrameSchema(
      fields,
      ["reference"],
      null,
      "manual-entry"
    );

    // Process rows to add filePaths
    const processedRows = validRows.map((row: any) => ({
      ...row,
      filePaths: Array.isArray(row.files) ? row.files : (row.files ? [row.files] : []),
    }));

    const tableData = new TableData(
      processedRows,
      schema,
      null
    );

    bibData.value.dataframeData = tableData;
    bibData.value.fileName = "manual-entry.csv";

    // Re-emit the bib update with the generated dataframe
    emitBibUpdate();
  };

  // Initialize component with existing data when navigating back
  const initializeWithExistingData = () => {
    // Set flag to prevent recursive updates
    isInitializing.value = true;

    // Initialize bibliography data
    if (props.initialBibData && (props.initialBibData.fileName || (props.initialBibData.dataframeData && props.initialBibData.dataframeData.data.length > 0))) {
      bibData.value = {
        fileName: props.initialBibData.fileName || "",
        dataframeData: props.initialBibData.dataframeData || null,
        rawContent: props.initialBibData.rawContent || "",
      };
    }

    // Initialize PDF data
    if (props.initialPdfData && (props.initialPdfData.matchedFiles.length > 0 || props.initialPdfData.unmatchedFiles.length > 0 || props.initialPdfData.totalFiles > 0)) {
      pdfData.value = {
        matchedFiles: props.initialPdfData.matchedFiles || [],
        unmatchedFiles: props.initialPdfData.unmatchedFiles || [],
        totalFiles: props.initialPdfData.totalFiles || 0,
      };
    }

    // Clear the initialization flag and emit updates after all data is set
    nextTick(() => {
      isInitializing.value = false;
      // Emit updates to parent to ensure consistency
      emitBibUpdate();
      emitPdfUpdate();
    });
  };

  // Public methods for parent components
  const reset = () => {
    // Set flag to prevent recursive updates during reset
    isInitializing.value = true;

    // Reset bibliography data
    bibData.value = {
      fileName: "",
      dataframeData: null,
      rawContent: "",
    };

    // Reset PDF data
    pdfData.value = {
      matchedFiles: [],
      unmatchedFiles: [],
      totalFiles: 0,
    };

    // Clear the initialization flag and emit updates after reset
    nextTick(() => {
      isInitializing.value = false;
      emitBibUpdate();
      emitPdfUpdate();
    });
  };

  // Watch for initial data changes
  watch(
    () => props.initialBibData,
    (newData: any, oldData: any) => {
      // Only initialize if data has actually changed and we're not already initializing
      if (!isInitializing.value && newData && (newData.fileName || (newData.dataframeData && newData.dataframeData.data.length > 0))) {
        // Check if the data is actually different to avoid unnecessary updates
        const hasChanged = !oldData ||
          newData.fileName !== oldData.fileName ||
          (newData.dataframeData?.data?.length || 0) !== (oldData.dataframeData?.data?.length || 0);

        if (hasChanged) {
          initializeWithExistingData();
        }
      }
    },
    { deep: true, immediate: true }
  );

  watch(
    () => props.initialPdfData,
    (newData: any, oldData: any) => {
      // Only initialize if data has actually changed and we're not already initializing
      if (!isInitializing.value && newData && (newData.matchedFiles.length > 0 || newData.unmatchedFiles.length > 0)) {
        // Check if the data is actually different to avoid unnecessary updates
        const hasChanged = !oldData ||
          newData.matchedFiles.length !== oldData.matchedFiles.length ||
          newData.unmatchedFiles.length !== oldData.unmatchedFiles.length ||
          newData.totalFiles !== oldData.totalFiles;

        if (hasChanged) {
          initializeWithExistingData();
        }
      }
    },
    { deep: true, immediate: true }
  );

  return {
    // Reactive state
    isInitializing,
    bibData,
    pdfData,
    editableTableData,
    editableTable,

    // Computed
    isValid,
    shouldShowEditableTable,
    allPdfFileNames,
    unmappedPdfFiles,
    editableTableColumns,
    editableTableValidators,

    // Methods
    handleBibUpdate,
    handlePdfUpdate,
    handleTableCellEdit,
    handleTableBuilt,
    emitBibUpdate,
    emitPdfUpdate,
    updateDataframeWithFilePaths,
    initializeEditableTable,
    syncEditableTableToBibData,
    initializeWithExistingData,
    reset,
  };
};