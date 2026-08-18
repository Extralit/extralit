/**
 * Extracted document layout, mirroring the server's `DoclingDocument` projection.
 *
 * Every bounding box is in page points with a top-left origin, relative to the `LayoutPage`
 * of the same `pageNo` — a viewer must scale by its own rendered page size, never assume 72dpi.
 */

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export class BoundingBox {
  constructor(
    public readonly l: number,
    public readonly t: number,
    public readonly r: number,
    public readonly b: number,
    public readonly coordOrigin: string = "TOPLEFT"
  ) {}

  get width(): number {
    return this.r - this.l;
  }

  get height(): number {
    return this.b - this.t;
  }

  /** Scale into the coordinate space of a rendered page of the given size. */
  toRect(pageWidth: number, pageHeight: number, renderedWidth?: number, renderedHeight?: number): Rect {
    const scaleX = (renderedWidth ?? pageWidth) / pageWidth;
    const scaleY = (renderedHeight ?? pageHeight) / pageHeight;

    return {
      left: this.l * scaleX,
      top: this.t * scaleY,
      width: this.width * scaleX,
      height: this.height * scaleY,
    };
  }

  /** Fractions of the page, for overlays that position with percentages. */
  toRelativeRect(pageWidth: number, pageHeight: number): Rect {
    return this.toRect(pageWidth, pageHeight, 1, 1);
  }
}

export class Provenance {
  constructor(
    public readonly pageNo: number,
    public readonly bbox: BoundingBox,
    /** Item-local character span — an offset into this item's own text, not the document. */
    public readonly charspan: [number, number]
  ) {}
}

export class LayoutItem {
  constructor(
    /** Citation anchor, e.g. `#/texts/12`. Stable for the lifetime of the stored layout. */
    public readonly selfRef: string,
    public readonly label: string,
    public readonly readingOrder: number,
    public readonly prov: Provenance[] = [],
    public readonly parentRef: string | null = null,
    public readonly contentLayer: string | null = null,
    public readonly level: number | null = null,
    public readonly text: string | null = null,
    public readonly html: string | null = null
  ) {}

  /** Every page this item touches; more than one when it spans a page break. */
  get pageNumbers(): number[] {
    return [...new Set(this.prov.map((p) => p.pageNo))].sort((a, b) => a - b);
  }

  get isTable(): boolean {
    return this.label === "table";
  }

  get isPicture(): boolean {
    return this.label === "picture";
  }

  get isHeading(): boolean {
    return this.label === "section_header" || this.label === "title";
  }

  provenanceOnPage(pageNo: number): Provenance[] {
    return this.prov.filter((p) => p.pageNo === pageNo);
  }
}

export class LayoutPage {
  constructor(
    public readonly pageNo: number,
    public readonly width: number,
    public readonly height: number
  ) {}
}

export class DocumentLayout {
  constructor(
    public readonly documentId: string,
    public readonly doclingVersion: string,
    public readonly pages: LayoutPage[] = [],
    public readonly items: LayoutItem[] = []
  ) {}

  get numPages(): number {
    return this.pages.length;
  }

  get numItems(): number {
    return this.items.length;
  }

  page(pageNo: number): LayoutPage | undefined {
    return this.pages.find((p) => p.pageNo === pageNo);
  }

  itemsOnPage(pageNo: number): LayoutItem[] {
    return this.items.filter((item) => item.pageNumbers.includes(pageNo));
  }

  itemByRef(selfRef: string): LayoutItem | undefined {
    return this.items.find((item) => item.selfRef === selfRef);
  }
}
