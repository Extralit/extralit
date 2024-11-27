import { DataFrameField, DataFrameSchema } from "./Schema";
import { ValidationSchema } from "./Validation";


export type Data = Array<{ [field: string]: any }>;

export type ReferenceValues = Record<string, Record<string, Data>>;

export class TableData {
    data: Data;
    schema: DataFrameSchema;
    reference?: string;
    validation?: ValidationSchema;
    columnUniqueCounts?: Record<string, number>;

    constructor(data: Data = [], schema: DataFrameSchema = new DataFrameSchema(), reference?: string) {
        this.data = data;
        this.schema = schema;
        this.reference = reference;
    }

    addRow(rowData: Record<string, any>) {
        this.data.push(rowData);
    }

    deleteRow(index: number) {
        this.data.splice(index, 1);
    }

    updateRow(index: number, rowData: Record<string, any>) {
        this.data[index] = { ...this.data[index], ...rowData };
    }

    addColumn(field: DataFrameField, defaultValue: any = null) {
        this.schema.addField(field);
        this.data.forEach(row => {
            row[field.name] = defaultValue;
        });
    }

    deleteColumn(fieldName: string) {
        this.schema.removeField(fieldName);
        this.data.forEach(row => {
            delete row[fieldName];
        });
    }

    renameColumn(oldName: string, newName: string) {
        this.schema.renameField(oldName, newName);
        this.data.forEach(row => {
            row[newName] = row[oldName];
            delete row[oldName];
        });
    }

    get columns(): string[] {
        return this.schema.fieldNames;
    }

    toJSON() {
        return {
            data: this.data,
            schema: this.schema,
            reference: this.reference,
            validation: this.validation,
            columnUniqueCounts: this.columnUniqueCounts
        };
    }
}


