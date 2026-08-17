import type { AxiosInstance } from "axios";
import { Document, Segment, type Segments } from "@/v1/domain/entities/document/Document";
import {
  BoundingBox,
  DocumentLayout,
  LayoutItem,
  LayoutPage,
  Provenance,
} from "@/v1/domain/entities/document/DocumentLayout";

const DOCUMENT_API_ERRORS = {
  ERROR_FETCHING_DOCUMENT: "ERROR_FETCHING_DOCUMENT",
  ERROR_LISTING_DOCUMENTS: "ERROR_LISTING_DOCUMENTS",
  ERROR_FETCHING_SEGMENTS: "ERROR_FETCHING_SEGMENTS",
  ERROR_FETCHING_LAYOUT: "ERROR_FETCHING_LAYOUT",
};

interface BackendBoundingBox {
  l: number;
  t: number;
  r: number;
  b: number;
  coord_origin: string;
}

interface BackendProvenance {
  page_no: number;
  bbox: BackendBoundingBox;
  charspan: [number, number];
}

interface BackendLayoutItem {
  self_ref: string;
  parent_ref: string | null;
  label: string;
  content_layer: string | null;
  level: number | null;
  reading_order: number;
  text: string | null;
  html: string | null;
  prov: BackendProvenance[];
}

interface BackendLayoutPage {
  page_no: number;
  width: number;
  height: number;
}

interface BackendDocumentLayout {
  document_id: string;
  docling_version: string;
  num_items: number;
  num_pages: number;
  pages: BackendLayoutPage[];
  items: BackendLayoutItem[];
}

const toBoundingBox = (bbox: BackendBoundingBox): BoundingBox =>
  new BoundingBox(bbox.l, bbox.t, bbox.r, bbox.b, bbox.coord_origin ?? "TOPLEFT");

const toProvenance = (prov: BackendProvenance): Provenance =>
  new Provenance(prov.page_no, toBoundingBox(prov.bbox), prov.charspan);

const toLayoutItem = (item: BackendLayoutItem): LayoutItem =>
  new LayoutItem(
    item.self_ref,
    item.label,
    item.reading_order,
    (item.prov ?? []).map(toProvenance),
    item.parent_ref ?? null,
    item.content_layer ?? null,
    item.level ?? null,
    item.text ?? null,
    item.html ?? null
  );

const toLayoutPage = (page: BackendLayoutPage): LayoutPage => new LayoutPage(page.page_no, page.width, page.height);

const toDocumentLayout = (layout: BackendDocumentLayout): DocumentLayout =>
  new DocumentLayout(
    layout.document_id,
    layout.docling_version,
    (layout.pages ?? []).map(toLayoutPage),
    (layout.items ?? []).map(toLayoutItem)
  );

export class DocumentRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getDocuments(params: {
    workspace_id: string;
    doc_id?: string;
    pmid?: string;
    doi?: string;
    reference?: string;
  }): Promise<Document[]> {
    try {
      const queryParams = Object.fromEntries(Object.entries(params).filter(([_, value]) => value !== undefined));

      if (Object.keys(queryParams).length === 0) {
        throw new Error("At least one identifier parameter must be provided");
      }

      const { data } = await this.axios.get<Document[]>("/v1/documents", {
        params: queryParams,
      });
      return data;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      };
    }
  }

  async getDocumentSegments(workspace: string, reference: string): Promise<Segment[]> {
    try {
      const { data } = await this.axios.get<Segments>("/v1/models/segments/", {
        params: { workspace, reference },
      });

      return data.items;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_SEGMENTS,
      };
    }
  }

  async getDocumentsByWorkspace(workspaceId: string): Promise<Document[]> {
    try {
      const { data } = await this.axios.get<Document[]>(`/v1/documents/workspace/${workspaceId}`);
      return data;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_LISTING_DOCUMENTS,
      };
    }
  }

  async getDocumentLayout(
    documentId: string,
    filters?: { pages?: number[]; labels?: string[] }
  ): Promise<DocumentLayout> {
    try {
      const params: Record<string, unknown> = {};
      if (filters?.pages?.length) params.pages = filters.pages;
      if (filters?.labels?.length) params.labels = filters.labels;

      // FastAPI binds repeated bare keys; axios' default `pages[]=` bracket form is silently dropped.
      const { data } = await this.axios.get<BackendDocumentLayout>(`/v1/documents/${documentId}/layout`, {
        params,
        paramsSerializer: { indexes: null },
      });

      return toDocumentLayout(data);
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_LAYOUT,
      };
    }
  }
}
