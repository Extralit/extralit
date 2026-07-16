import ImportAnalysisTable from "./ImportAnalysisTable.vue";
import ImportFlow from "../ImportFlow.vue";

describe("ImportAnalysisTable document actions", () => {
  it("restores persisted actions when the review step is remounted", () => {
    const component = ImportAnalysisTable as any;
    const state = component.data.call({ initialDocumentActions: { keep: "ignore" } });

    expect(state.localDocumentActions).toEqual({ keep: "ignore" });
    expect(state.editableTableData).toEqual([]);
  });

  it("keeps only persisted actions that belong to the latest analysis", () => {
    const component = ImportAnalysisTable as any;
    const context = {
      initialDocumentActions: { keep: "ignore", stale: "update" },
      localDocumentActions: {},
      $emit: vi.fn(),
      emitUpdate: vi.fn(),
    };

    component.watch.analysisResult.handler.call(context, {
      documents: { keep: {} },
    });

    expect(context.localDocumentActions).toEqual({ keep: "ignore" });
    expect(context.$emit).toHaveBeenCalledWith("analysis-complete", { documents: { keep: {} } });
    expect(context.emitUpdate).toHaveBeenCalledOnce();
  });
});

describe("ImportFlow input changes", () => {
  it("clears persisted actions when the bibliography or PDFs change", () => {
    const component = ImportFlow as any;
    const context = {
      bibData: {},
      pdfData: {},
      uploadData: { documentActions: { previous: "ignore" } },
      clearError: vi.fn(),
    };

    component.methods.handleBibUpdate.call(context, { fileName: "new.bib" });
    expect(context.uploadData.documentActions).toEqual({});

    context.uploadData.documentActions = { previous: "ignore" };
    component.methods.handlePdfUpdate.call(context, { totalFiles: 1 });
    expect(context.uploadData.documentActions).toEqual({});
  });
});
