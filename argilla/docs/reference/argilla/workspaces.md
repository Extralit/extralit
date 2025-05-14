---
hide: footer
---

# `rg.Workspace`

In Argilla, workspaces are used to organize datasets in to groups. For example, you might have a workspace for each project or team.

## Usage Examples

To create a new workspace, instantiate the `Workspace` object with the client and the name:

```python
workspace = rg.Workspace(name="my_workspace")
workspace.create()
```

To retrieve an existing workspace, use the `client.workspaces` attribute:

```python
workspace = client.workspaces("my_workspace")
```

## File Operations

### List Files

List files in a workspace.

```python
# Get a workspace reference
workspace = client.workspaces(name="my-workspace")

# List files with optional parameters
files = workspace.list_files(path="", recursive=True, include_version=True)

# Access the files
for file in files.objects:
    print(f"File: {file.object_name}, Size: {file.size}, Last Modified: {file.last_modified}")
```

### Get File

Get a file from a workspace.

```python
workspace = client.workspaces(name="my-workspace")
file_response = workspace.get_file(path="path/to/file.txt", version_id=None)

# Access the file content
content = file_response.content

# Access the file metadata
metadata = file_response.metadata
print(f"Content Type: {metadata.content_type}, ETag: {metadata.etag}")
```

### Upload File

Upload a file to a workspace.

```python
workspace = client.workspaces(name="my-workspace")
file_metadata = workspace.put_file(path="path/to/store/file.txt", file_path="/local/path/to/file.txt")

print(f"File uploaded: {file_metadata.object_name}")
```

### Delete File

Delete a file from a workspace.

```python
workspace = client.workspaces(name="my-workspace")
workspace.delete_file(path="path/to/file.txt", version_id=None)
```

## Document Operations

### Add Document

Add a document to a workspace.

```python
workspace = client.workspaces(name="my-workspace")

# Add a document with a URL
document_id = workspace.add_document(url="https://example.com/document.pdf")

# Add a document with a PMID
document_id = workspace.add_document(pmid="PMC12345")

# Add a document with a DOI
document_id = workspace.add_document(doi="10.1234/example")

# Add a document with a file
document_id = workspace.add_document(file_path="/local/path/to/document.pdf")
```

### Get Documents

Get documents from a workspace.

```python
workspace = client.workspaces(name="my-workspace")
documents = workspace.get_documents()

# Access the documents
for doc in documents:
    print(f"Document ID: {doc.id}, URL: {doc.url}, PMID: {doc.pmid}, DOI: {doc.doi}")
```

## Schema Operations

### Get Schemas

Get schemas from a workspace.

```python
workspace = client.workspaces(name="my-workspace")
schemas = workspace.get_schemas(prefix="schemas/", exclude=None)

# Access the schemas
for schema in schemas.schemas:
    print(f"Schema: {schema.name}")
    print(f"Columns: {list(schema.columns.keys())}")
```

### Add Schema

Add a schema to a workspace.

```python
import pandera as pa

# Create a schema
schema = pa.DataFrameSchema(
    name="my_schema",
    columns={
        "text": pa.Column(pa.String),
        "label": pa.Column(pa.String),
        "score": pa.Column(pa.Float, nullable=True),
    },
)

# Add the schema to the workspace
workspace = client.workspaces(name="my-workspace")
workspace.add_schema(schema, prefix="schemas/")
```

### Update Schemas

Update schemas in a workspace.

```python
import pandera as pa
from extralit.extraction.models import SchemaStructure

# Create schemas
schema1 = pa.DataFrameSchema(
    name="schema1",
    columns={
        "text": pa.Column(pa.String),
        "label": pa.Column(pa.String),
    },
)

schema2 = pa.DataFrameSchema(
    name="schema2",
    columns={
        "text": pa.Column(pa.String),
        "score": pa.Column(pa.Float),
    },
)

# Create a schema structure
schemas = SchemaStructure(schemas=[schema1, schema2])

# Update schemas in the workspace
workspace = client.workspaces(name="my-workspace")
result = workspace.update_schemas(schemas, check_existing=True, prefix="schemas/")

print(f"Updated {len(result.objects)} schemas")
```

## Error Handling

All API methods include proper error handling. If an error occurs, an exception will be raised with a descriptive error message.

```python
try:
    workspace = client.workspaces(name="non-existent-workspace")
    files = workspace.list_files("")
except Exception as e:
    print(f"Error: {str(e)}")
```

---

::: src.argilla.workspaces._resource.Workspace
    options:
        heading_level: 4
