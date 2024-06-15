import { LabelAnswer } from "../IAnswer";

export class Segment {
	constructor(
		public readonly doc_id: string | number,
		public readonly header: string | null,
		public readonly page_number: number | null,
		public readonly type: string | null,
	) {}

	public static getDescription(segment: Segment): string {
			let segmentDescription = Object.entries(segment)
					.filter(([key, value]) => !['header', 'doc_id'].includes(key))
					.map(([key, value]) => `${key}: ${value}`)
					.join('\n');
			return segmentDescription;
	}
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
		public reference?: string,
		public segments?: Segment[],
	) {
		this.segments = segments || [];
	}

	getQuestionSelections(): LabelAnswer[] {
		if (!this.segments) {
			return null;
		}

		const selections = this.segments
			?.filter((segment) => segment?.header)
			?.reduce((unique, segment) => {
				if (!segment?.header || unique.some(item => item.header === segment.header)) return unique;
				return [...unique, segment];
			}, [])
			.map((segment) => {
				return { 
					value: segment.header, 
					text: segment.header, 
					description: Segment.getDescription(segment),
				}
			});
		
		return selections;
	}
}
