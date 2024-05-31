import { LabelAnswer } from "../IAnswer";

export class Segment {
  constructor(
    public readonly doc_id: string | number,
    public readonly header: string | null,
    public readonly page_number: number | null,
    public readonly type: string | null,
  ) {}
}

export interface Segments {
  items: Segment[];
}

export class Document {
	constructor(
		public readonly id: string,
		public readonly url?: string,
		public readonly file_name?: string,
		public readonly pmid?: string,
		public readonly page_number?: number | string,
		public segments?: Segment[],
	) {
		this.segments = segments || [];
	}

	getQuestionSelections(): LabelAnswer[] {
		if (!this.segments) {
			return null;
		}

		const selections = this.segments
			?.filter((segment: Segment) => segment?.header)
			.map((segment: Segment) => 
				({ value: segment.header, text: segment.header, description: `Page ${segment.page_number}`}));
		
		return selections;
	}
}
