
export class Document {
	constructor(
		public readonly id: string,
		public readonly file_data: Blob,
		public readonly file_name?: string,
		public readonly pmid?: string,
	) {}

	// methods like isModified(), submit(), etc
}
	