
export class Document {
	constructor(
		public readonly id: string,
		public readonly url?: string,
		public readonly file_name?: string,
		public readonly pmid?: string,
		public readonly page_number?: number | string,
	) {}

}
	