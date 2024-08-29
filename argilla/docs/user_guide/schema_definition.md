---
description: Learn how to define schemas in Extralit to extract structured data from scientific papers.
---

# Schema Definition

In Extralit, schemas are defined using [Pandera's DataFrameModel](https://pandera.readthedocs.io/en/stable/dataframe_models.html). These schemas specify the structure and validation rules for the data you want to extract from each scientific paper reference. This guide will walk you through the process of defining a schema, explaining each component in detail.

> **Note**: Before diving into schema definition, make sure you understand the concept of references in Extralit. References are unique identifiers for each scientific paper in your dataset. Learn more about references and other core concepts in the [Core Concepts](../core_concepts.md) guide.


## Basic Usage

Let's start with two basic examples of schema definitions: one for document-level extraction and another for table extraction.

### Document-Level Extraction

This type of schema is used for information that appears only once per paper:

```python
import pandas as pd
import pandera as pa
from pandera.typing import Index, DataFrame, Series

class Publication(pa.DataFrameModel):
    """
    General information about the publication, extracted once per paper.
    """
    reference: Index[str] = pa.Field(unique=True, check_name=True)
    title: Series[str] = pa.Field()
    authors: Series[str] = pa.Field()
    journal: Series[str] = pa.Field()
    publication_year: Series[int] = pa.Field(ge=1900, le=2100)
    doi: Series[str] = pa.Field(nullable=True)
    
    class Config:
        singleton = {'enabled': True}  # Indicates this is a document-level schema
```

### Table Extraction

This type of schema is used for information that may appear multiple times in a paper:

```python
class StudyDesign(pa.DataFrameModel):
    """
    Study design details for one or more experimental setup.
    """
    year: Series[int] = pa.Field(gt=2000, coerce=True)
    month: Series[int] = pa.Field(ge=1, le=12, coerce=True)
    day: Series[int] = pa.Field(ge=0, le=365, coerce=True)
    sample_size: Series[int] = pa.Field(gt=0)
```

Let's break down this schema definition:

### 1. Imports

```python
import pandas as pd
import pandera as pa
from pandera.typing import Index, DataFrame, Series
```

These imports bring in the necessary modules:
- `pandas` for data manipulation
- `pandera` for schema definition
- `Index`, `DataFrame`, and `Series` from `pandera.typing` for type hinting

### 2. Class Definition

```python
class StudyDesign(pa.DataFrameModel):
    """
    Study design details for one or more experimental setup that are often found in methodology sections.
    """
```

This defines a new `pa.DataFrameModel` class named `StudyDesign` that represents a table to be extracted from each paper reference. Important points:

- The class represents a specific type of information (study design) that may appear multiple times in a single paper.
- The docstring provides context for the LLM, guiding it to look for specific types of information (i.e. experimental setup) and where to find it (methodology sections).
- Multiple instances of this schema may be extracted from a single paper if multiple study designs are described.

### 3. Column Definitions

Each line within the class defines a column in our schema:

```python
year: Series[int] = pa.Field(gt=2000, coerce=True)
```

Let's break this down:

- `year`: This is the name of the column.
- `Series[int]`: This specifies that the column should be a pandas Series containing integer values.
- `pa.Field()`: This is where we define validation rules and other properties for the column.

### 4. Validation Rules

Inside `pa.Field()`, we specify validation rules:

- `gt=2000`: This means the value should be greater than 2000.
- `coerce=True`: This tells Pandera to try to convert (coerce) the input to the specified type (int in this case) if it's not already of that type.

Similarly, for the `month` column:

```python
month: Series[int] = pa.Field(ge=1, le=12, coerce=True)
```

- `ge=1`: Greater than or equal to 1
- `le=12`: Less than or equal to 12

These rules ensure that the month is always an integer between 1 and 12.

## Advanced Usage

Let's extend our schema with more advanced features, incorporating best practices to ensure data quality and consistency:

```python
class StudyDesign(pa.DataFrameModel):
    """
    Study design details for one or more experimental setup that are often found in methodology sections.
    This schema includes best practices for extracting structured data from scientific papers.
    """
    study_id: Index[str] = pa.Field(
        unique=True, 
        str_length={'min_length': 5, 'max_length': 10},
        check_name=True
    )
    year: Series[int] = pa.Field(ge=1900, le=2100, coerce=True)
    month: Series[int] = pa.Field(ge=1, le=12, coerce=True)
    day: Series[int] = pa.Field(ge=1, le=31, coerce=True)
    sample_size: Series[int] = pa.Field(gt=0)
    study_type: Series[str] = pa.Field(
        isin=['RCT', 'Observational', 'Meta-analysis'],
        description="The type of study conducted",
        nullable=False
    )
    
    @pa.check('sample_size')
    def check_sample_size(cls, sample_size: Series[int]) -> Series[bool]:
        return sample_size % 2 == 0  # Ensure sample size is even
    
    class Config:
        strict = True
        coerce = True
```

New features in this advanced schema:

1. **String Length Validation**: 
    ```python
    study_id: Index[str] = pa.Field(unique=True, str_length={'min_length': 5, 'max_length': 10},check_name=True)
    ```
    This ensures the `study_id` is a string between 5 and 10 characters long.

2. **Nullable Fields**:
     ```python
     month: Series[int] = pa.Field(ge=1, le=12, nullable=True, coerce=True)
     ```
    Allowing certain fields to be nullable acknowledges that not all information may be available in every paper.

3. **Categorical Validation**:
    ```python
    study_type: Series[str] = pa.Field(isin=['RCT', 'Observational', 'Meta-analysis'])
    ```
    This restricts `study_type` to only these three values.


4. **Field Descriptions**:
    ```python
    study_type: Series[str] = pa.Field(
        isin=['RCT', 'Observational', 'Meta-analysis'],
        description="The type of study conducted",
        nullable=False
    )
    ```
    Adding descriptions to fields helps guide the extraction process and provides context for the LLM and data annotators.


5. **Custom Validation Check**:
    ```python
    @pa.check('sample_size')
    def check_sample_size(cls, sample_size: Series[int]) -> Series[bool]:
         return sample_size % 2 == 0  # Ensure sample size is even
    ```
    This custom check ensures that the sample size is always even.

6. **Configuration**:
    ```python
    class Config:
         strict = True
         coerce = True
    ```
    - `strict = True`: Ensures no additional columns are allowed beyond what's defined in the schema.
    - `coerce = True`: Applies type coercion to all fields by default.

## Using the Schema

Once defined, you can use this schema to validate your data:

```python
import pandas as pd

data = pd.DataFrame({
    'study_id': ['STUDY001', 'STUDY002'],
    'year': [2022, 2023],
    'month': [6, 12],
    'day': [15, 31],
    'sample_size': [100, 200],
    'study_type': ['RCT', 'Observational']
})

validated_data = StudyDesign.validate(data)
```

If the data doesn't meet the schema requirements, Pandera will raise an informative error, helping you identify and correct issues in your extracted data.

## Best Practices

1. **Start Simple**: Begin with basic type and range validations, then add more complex rules as needed.

2. **Use Descriptive Names**: Choose clear, descriptive names for your schema classes and fields.

3. **Use Schema Descriptions**: Include a detailed docstring for your schema class. This helps guide the LLM in understanding what type of information to extract and where to find it in the paper.

4. **Leverage Field Metadata**: Use the description parameter in pa.Field() to provide context for each field. This can help guide the extraction process and provide valuable information for data users.

5. **Use Appropriate Data Types**: Choose the most specific data type possible for each field. For example, use int for whole numbers and float for decimal values.

6. **Implement Logical Constraints**: Use multi-field checks to ensure logical consistency between related fields.
   
7. **Allow for Flexibility**: Use nullable=True for fields that may not always be present in every paper. This acknowledges the variability in reporting across different studies.

8. **Test Your Schema**: Create validate your schema to a small dataset to ensure the checks behave as expected with various input data.

By defining clear and comprehensive schemas, you ensure that the data extracted by Extralit is consistent, valid, and ready for analysis. This approach significantly reduces data cleaning efforts and improves the overall quality of your research data.