import { DataFrameSchema } from "@/v1/domain/entities/table/Schema";
import { TableData } from "@/v1/domain/entities/table/TableData";

/**
 * Utility for determining schema topological ordering based on field references
 */
export class SchemaOrderingUtil {
  /**
   * Extract reference dependencies from a schema
   * @param schema The schema to analyze
   * @returns Array of schema names that this schema depends on
   */
  static extractDependencies(schema: DataFrameSchema): string[] {
    const dependencies: string[] = [];
    const schemaName = schema.schemaName?.toLowerCase() || '';
    
    schema.fields.forEach(field => {
      const fieldName = field.name;
      
      // Check for _ref suffix pattern
      if (fieldName.endsWith('_ref')) {
        const referencedSchema = fieldName.replace(/_ref$/, '');
        if (referencedSchema !== schemaName) {
          dependencies.push(referencedSchema);
        }
      }
      
      // Check for _ID pattern (but not self-referencing)
      if (fieldName.endsWith('_ID') && !fieldName.toLowerCase().startsWith(schemaName)) {
        const referencedSchema = fieldName.replace(/_ID$/, '');
        dependencies.push(referencedSchema);
      }
    });
    
    return [...new Set(dependencies)]; // Remove duplicates
  }

  /**
   * Extract schema name from table data or field name
   * @param tableData The table data to extract schema name from
   * @returns The schema name or null if not found
   */
  static extractSchemaName(tableData: TableData): string | null {
    return tableData.schema?.schemaName || null;
  }

  /**
   * Build dependency graph from multiple schemas
   * @param schemas Array of schema objects to analyze
   * @returns Map of schema name to its dependencies
   */
  static buildDependencyGraph(schemas: DataFrameSchema[]): Map<string, string[]> {
    const graph = new Map<string, string[]>();
    
    schemas.forEach(schema => {
      const schemaName = schema.schemaName;
      if (schemaName) {
        const dependencies = this.extractDependencies(schema);
        graph.set(schemaName, dependencies);
      }
    });
    
    return graph;
  }

  /**
   * Perform topological sort on schemas based on their dependencies
   * @param dependencyGraph Map of schema name to its dependencies
   * @returns Array of schema names in topological order
   */
  static topologicalSort(dependencyGraph: Map<string, string[]>): string[] {
    const visited = new Set<string>();
    const visiting = new Set<string>();
    const result: string[] = [];

    const visit = (schemaName: string): void => {
      if (visiting.has(schemaName)) {
        // Circular dependency detected, skip to avoid infinite loop
        console.warn(`Circular dependency detected involving schema: ${schemaName}`);
        return;
      }
      
      if (visited.has(schemaName)) {
        return;
      }

      visiting.add(schemaName);
      
      const dependencies = dependencyGraph.get(schemaName) || [];
      dependencies.forEach(dep => {
        if (dependencyGraph.has(dep)) {
          visit(dep);
        }
      });

      visiting.delete(schemaName);
      visited.add(schemaName);
      result.push(schemaName);
    };

    // Visit all schemas
    Array.from(dependencyGraph.keys()).forEach(schemaName => {
      if (!visited.has(schemaName)) {
        visit(schemaName);
      }
    });

    return result;
  }

  /**
   * Get ordered schema names from table data array
   * @param tableDatas Array of table data objects
   * @returns Array of schema names in dependency order
   */
  static orderSchemas(tableDatas: TableData[]): string[] {
    const schemas = tableDatas
      .map(td => td.schema)
      .filter(schema => schema && schema.schemaName);

    const dependencyGraph = this.buildDependencyGraph(schemas);
    return this.topologicalSort(dependencyGraph);
  }

  /**
   * Sort table data array by schema dependencies
   * @param tableDatas Array of table data objects to sort
   * @returns Sorted array with dependencies first
   */
  static sortTableDataByDependencies(tableDatas: TableData[]): TableData[] {
    const orderedSchemaNames = this.orderSchemas(tableDatas);
    const schemaOrder = new Map(orderedSchemaNames.map((name, index) => [name, index]));

    return [...tableDatas].sort((a, b) => {
      const aSchemaName = a.schema?.schemaName || '';
      const bSchemaName = b.schema?.schemaName || '';
      
      const aOrder = schemaOrder.get(aSchemaName) ?? 999;
      const bOrder = schemaOrder.get(bSchemaName) ?? 999;
      
      return aOrder - bOrder;
    });
  }

  /**
   * Group and sort field names by their schema prefix
   * @param fieldNames Array of field names to organize
   * @returns Object with schema names as keys and field arrays as values, in dependency order
   */
  static groupFieldsBySchema(fieldNames: string[]): Record<string, string[]> {
    const groups: Record<string, string[]> = {};
    
    fieldNames.forEach(fieldName => {
      // Extract schema prefix (assumes format like "schema_name-field_name")
      const schemaPrefixMatch = fieldName.match(/^([^-]+)-/);
      const schemaPrefix = schemaPrefixMatch ? schemaPrefixMatch[1] : 'other';
      
      if (!groups[schemaPrefix]) {
        groups[schemaPrefix] = [];
      }
      groups[schemaPrefix].push(fieldName);
    });

    return groups;
  }
}