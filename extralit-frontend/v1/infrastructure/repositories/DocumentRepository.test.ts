import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { DocumentRepository } from "./DocumentRepository";

const axiosMock = (getImpl: (url: string) => unknown) =>
  ({ get: vi.fn(async (url: string) => ({ data: getImpl(url) })) }) as unknown as AxiosInstance;

const rejectingAxiosMock = () =>
  ({ get: vi.fn(async () => Promise.reject(new Error("boom"))) }) as unknown as AxiosInstance;

const BACKEND_LAYOUT = {
  document_id: "d-1",
  docling_version: "1.10.0",
  num_items: 3,
  num_pages: 2,
  pages: [
    { page_no: 1, width: 612, height: 792 },
    { page_no: 2, width: 612, height: 792 },
  ],
  items: [
    {
      self_ref: "#/texts/0",
      parent_ref: "#/body",
      label: "section_header",
      content_layer: "body",
      level: 2,
      reading_order: 0,
      text: "Methods",
      html: null,
      prov: [
        {
          page_no: 1,
          bbox: { l: 72, t: 54, r: 300, b: 72, coord_origin: "TOPLEFT" },
          charspan: [0, 7],
        },
      ],
    },
    {
      self_ref: "#/tables/0",
      parent_ref: "#/body",
      label: "table",
      content_layer: "body",
      level: null,
      reading_order: 1,
      text: null,
      html: "<table><tbody><tr><td>a</td></tr></tbody></table>",
      // A table that runs across a page break carries one entry per page.
      prov: [
        { page_no: 1, bbox: { l: 72, t: 600, r: 372, b: 792, coord_origin: "TOPLEFT" }, charspan: [0, 0] },
        { page_no: 2, bbox: { l: 72, t: 0, r: 372, b: 200, coord_origin: "TOPLEFT" }, charspan: [0, 0] },
      ],
    },
    {
      self_ref: "#/pictures/0",
      parent_ref: "#/body",
      label: "picture",
      content_layer: "body",
      level: null,
      reading_order: 2,
      text: null,
      html: null,
      prov: [{ page_no: 2, bbox: { l: 72, t: 300, r: 192, b: 390, coord_origin: "TOPLEFT" }, charspan: [0, 0] }],
    },
  ],
};

describe("DocumentRepository", () => {
  describe("getDocumentLayout", () => {
    it("fetches the layout and maps it to domain entities", async () => {
      const axios = axiosMock(() => BACKEND_LAYOUT);
      const repository = new DocumentRepository(axios);

      const layout = await repository.getDocumentLayout("d-1");

      expect(axios.get).toHaveBeenCalledWith("/v1/documents/d-1/layout", {
        params: {},
        paramsSerializer: { indexes: null },
      });
      expect(layout.documentId).toBe("d-1");
      expect(layout.doclingVersion).toBe("1.10.0");
      expect(layout.numPages).toBe(2);
      expect(layout.numItems).toBe(3);
    });

    it("maps snake_case provenance onto the camelCase domain shape", async () => {
      const repository = new DocumentRepository(axiosMock(() => BACKEND_LAYOUT));

      const layout = await repository.getDocumentLayout("d-1");
      const heading = layout.itemByRef("#/texts/0");

      expect(heading.selfRef).toBe("#/texts/0");
      expect(heading.parentRef).toBe("#/body");
      expect(heading.readingOrder).toBe(0);
      expect(heading.contentLayer).toBe("body");
      expect(heading.level).toBe(2);
      expect(heading.text).toBe("Methods");
      expect(heading.html).toBeNull();
      expect(heading.prov[0].pageNo).toBe(1);
      expect(heading.prov[0].charspan).toEqual([0, 7]);
    });

    it("keeps text and html on the field each belongs to", async () => {
      const layout = await new DocumentRepository(axiosMock(() => BACKEND_LAYOUT)).getDocumentLayout("d-1");
      const table = layout.itemByRef("#/tables/0");

      expect(table.text).toBeNull();
      expect(table.html).toBe("<table><tbody><tr><td>a</td></tr></tbody></table>");
    });

    it("passes page and label filters as query params", async () => {
      const axios = axiosMock(() => BACKEND_LAYOUT);
      const repository = new DocumentRepository(axios);

      await repository.getDocumentLayout("d-1", { pages: [2], labels: ["table"] });

      expect(axios.get).toHaveBeenCalledWith("/v1/documents/d-1/layout", {
        params: { pages: [2], labels: ["table"] },
        paramsSerializer: { indexes: null },
      });
    });

    it("omits empty filters rather than sending empty arrays", async () => {
      const axios = axiosMock(() => BACKEND_LAYOUT);
      const repository = new DocumentRepository(axios);

      await repository.getDocumentLayout("d-1", { pages: [], labels: [] });

      expect(axios.get).toHaveBeenCalledWith("/v1/documents/d-1/layout", {
        params: {},
        paramsSerializer: { indexes: null },
      });
    });

    it("throws a typed error when the request fails", async () => {
      const repository = new DocumentRepository(rejectingAxiosMock());

      await expect(repository.getDocumentLayout("d-1")).rejects.toEqual({
        response: "ERROR_FETCHING_LAYOUT",
      });
    });
  });

  describe("DocumentLayout entity", () => {
    const layoutOf = async () => new DocumentRepository(axiosMock(() => BACKEND_LAYOUT)).getDocumentLayout("d-1");

    it("reports every page an item touches", async () => {
      const layout = await layoutOf();

      expect(layout.itemByRef("#/tables/0").pageNumbers).toEqual([1, 2]);
      expect(layout.itemByRef("#/pictures/0").pageNumbers).toEqual([2]);
    });

    it("returns the items that appear on a page", async () => {
      const layout = await layoutOf();

      expect(layout.itemsOnPage(1).map((i) => i.selfRef)).toEqual(["#/texts/0", "#/tables/0"]);
      expect(layout.itemsOnPage(2).map((i) => i.selfRef)).toEqual(["#/tables/0", "#/pictures/0"]);
    });

    it("returns only the provenance on the requested page", async () => {
      const layout = await layoutOf();

      const onPageTwo = layout.itemByRef("#/tables/0").provenanceOnPage(2);

      expect(onPageTwo).toHaveLength(1);
      expect(onPageTwo[0].bbox.t).toBe(0);
    });

    it("classifies items by label", async () => {
      const layout = await layoutOf();

      expect(layout.itemByRef("#/tables/0").isTable).toBe(true);
      expect(layout.itemByRef("#/pictures/0").isPicture).toBe(true);
      expect(layout.itemByRef("#/texts/0").isHeading).toBe(true);
    });

    it("exposes page geometry by page number", async () => {
      const layout = await layoutOf();

      expect(layout.page(1).height).toBe(792);
      expect(layout.page(99)).toBeUndefined();
    });
  });

  describe("BoundingBox geometry", () => {
    const bboxOf = async () =>
      (await new DocumentRepository(axiosMock(() => BACKEND_LAYOUT)).getDocumentLayout("d-1")).itemByRef("#/texts/0")
        .prov[0].bbox;

    it("computes width and height from the edges", async () => {
      const bbox = await bboxOf();

      expect(bbox.width).toBe(228);
      expect(bbox.height).toBe(18);
    });

    it("returns page-point coordinates when no rendered size is given", async () => {
      const bbox = await bboxOf();

      expect(bbox.toRect(612, 792)).toEqual({ left: 72, top: 54, width: 228, height: 18 });
    });

    it("scales into the rendered page size for an overlay", async () => {
      const bbox = await bboxOf();

      // A page rendered at double scale doubles every coordinate.
      expect(bbox.toRect(612, 792, 1224, 1584)).toEqual({ left: 144, top: 108, width: 456, height: 36 });
    });

    it("expresses the box as fractions of the page", async () => {
      const bbox = await bboxOf();
      const rect = bbox.toRelativeRect(612, 792);

      expect(rect.left).toBeCloseTo(72 / 612);
      expect(rect.top).toBeCloseTo(54 / 792);
      expect(rect.width).toBeCloseTo(228 / 612);
    });

    it("defaults the coordinate origin to top-left", async () => {
      const bbox = await bboxOf();

      expect(bbox.coordOrigin).toBe("TOPLEFT");
    });
  });
});
