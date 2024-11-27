export interface DataFrameField {
    name: string;
    type: string;
    extDtype?: string;
}

export interface SchemaMetadata {
    schemaName?: string;
    etag?: string;
    version_id?: string;
    last_modified?: Date;
    version_tag?: string;
    is_latest?: boolean;
}

export class DataFrameSchema {
    primaryKey: string[];
    fields: DataFrameField[];
    metadata?: SchemaMetadata;
    schemaName?: string;

    constructor(
        fields: DataFrameField[] = [], 
        primaryKey: string[] = [], 
        metadata?: SchemaMetadata
    ) {
        this.fields = fields;
        this.primaryKey = primaryKey;
        this.metadata = metadata;
    }

    get fieldNames(): string[] {
        return this.fields.map(f => f.name);
    }

    addField(field: DataFrameField) {
        if (!this.fields.find(f => f.name === field.name)) {
            this.fields.push(field);
        }
    }

    removeField(fieldName: string) {
        this.fields = this.fields.filter(f => f.name !== fieldName);
    }

    renameField(oldName: string, newName: string) {
        const field = this.fields.find(f => f.name === oldName);
        if (field) {
            field.name = newName;
        }
        if (this.primaryKey.includes(oldName)) {
            this.primaryKey = this.primaryKey.map(k => k === oldName ? newName : k);
        }
    }
}