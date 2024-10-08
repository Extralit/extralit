---
description: >-
  Learn how to define schemas in Extralit to extract structured data from
  scientific papers.
title: multi_schemas
---
# Customizing Multiple Extraction Schemas

While defining a <SwmLink doc-title="schema_definition" repo-id="Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA==" repo-name="extralit" path="/.swm/schema_definition.dj6vmntw.sw.md">[schema_definition](https://app.swimm.io/repos/Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA%3D%3D/docs/dj6vmntw)</SwmLink> are useful for many extraction tasks, there are scenarios where using multiple schemas can provide better organization and more accurate representation of the data. This guide will walk you through the process of creating and managing multiple schemas in Extralit.

## Why Use Multiple Schemas?

Multiple schemas are beneficial when:

1. Different parts of a paper contain distinct types of information.
2. There are one-to-many relationships between data points.
3. You want to establish relational links between different types of data.
4. You need to prevent data duplication and maintain data integrity.

### Example 1: Separating Study Design and Demographic Information

Let's consider a scenario where a scientific paper presents information about two studies, each with multiple demographic groups. If we try to capture all this information in a single schema, we might end up with redundant data entry.

Here's an example of what the data in the paper might look like:

<table border="1" cellpadding="5" cellspacing="0"> <tr> <th>Year</th> <th>Study Type</th> <th>Age Group</th> <th>Gender</th> <th>Count</th> </tr> <tr> <td>2020</td> <td>RCT</td> <td>Child</td> <td>Male</td> <td>50</td> </tr> <tr> <td>2020</td> <td>RCT</td> <td>Child</td> <td>Female</td> <td>55</td> </tr> <tr> <td>2020</td> <td>RCT</td> <td>Adult</td> <td>Male</td> <td>100</td> </tr> <tr> <td>2020</td> <td>RCT</td> <td>Adult</td> <td>Female</td> <td>95</td> </tr> <tr> <td>2021</td> <td>Observational</td> <td>Adult</td> <td>Male</td> <td>75</td> </tr> <tr> <td>2021</td> <td>Observational</td> <td>Adult</td> <td>Female</td> <td>80</td> </tr> <tr> <td>2021</td> <td>Observational</td> <td>Senior</td> <td>Male</td> <td>40</td> </tr> <tr> <td>2021</td> <td>Observational</td> <td>Senior</td> <td>Female</td> <td>45</td> </tr> </table>

If we were to use a single schema to capture this information, it might look like this:

```python
import pandera as pa
from pandera.typing import Series

class StudyDemographic(pa.DataFrameModel):
    year: Series[int] = pa.Field(ge=2000, le=2024)
    study_type: Series[str] = pa.Field(isin=['RCT', 'Observational', 'Meta-analysis'])
    age_group: Series[str] = pa.Field(isin=['Child', 'Adult', 'Senior'])
    gender: Series[str] = pa.Field(isin=['Male', 'Female', 'Other'])
    count: Series[int] = pa.Field(gt=0)
```

However, using this schema would require redundant manual data entry. Notice how we would have to repeat the study information (year and study_type) for each demographic entry. This redundancy can lead to data inconsistencies that is exacerbated as the number of demographic groups increase, and makes the data more difficult to update/correct.

To solve this, we can separate our schema into two:

```python
import pandera as pa
from pandera.typing import Series, Index

class StudyDesign(pa.DataFrameModel):
    StudyDesign_ID: Index[str] = pa.Field(unique=True)
    year: Series[int] = pa.Field(ge=2000, le=2023)
    sample_size: Series[int] = pa.Field(gt=0)
    study_type: Series[str] = pa.Field(isin=['RCT', 'Observational', 'Meta-analysis'])

class Demographic(pa.DataFrameModel):
    StudyDesign_ID: Series[str]  # This will be our foreign key
    age_group: Series[str] = pa.Field(isin=['Child', 'Adult', 'Senior'])
    gender: Series[str] = pa.Field(isin=['Male', 'Female', 'Other'])
    count: Series[int] = pa.Field(gt=0)
```

Note that we've introduced a `StudyDesign_ID` field in the `StudyDesign` and `Demographic` schemas, which serves as a foreign key linking `Demographic` data to the `StudyDesign` information.

Now, we can represent our data more efficiently:

<h4>Study Design Table</h4> <table border="1" cellpadding="5" cellspacing="0"> <tr> <th>StudyDesign_ID</th> <th>year</th> <th>study_type</th> </tr> <tr> <td>S01</td> <td>2020</td> <td>RCT</td> </tr> <tr> <td>S02</td> <td>2021</td> <td>Observational</td> </tr> </table>

<h4>Demographic Table</h4> <table border="1" cellpadding="5" cellspacing="0"> <tr> <th>StudyDesign_ID</th> <th>age_group</th> <th>gender</th> <th>count</th> </tr> <tr> <td>S01</td> <td>Child</td> <td>Male</td> <td>50</td> </tr> <tr> <td>S01</td> <td>Child</td> <td>Female</td> <td>55</td> </tr> <tr> <td>S01</td> <td>Adult</td> <td>Male</td> <td>100</td> </tr> <tr> <td>S01</td> <td>Adult</td> <td>Female</td> <td>95</td> </tr> <tr> <td>S02</td> <td>Adult</td> <td>Male</td> <td>75</td> </tr> <tr> <td>S02</td> <td>Adult</td> <td>Female</td> <td>80</td> </tr> <tr> <td>S02</td> <td>Senior</td> <td>Male</td> <td>40</td> </tr> <tr> <td>S02</td> <td>Senior</td> <td>Female</td> <td>45</td> </tr> </table>

This approach eliminates redundancy in the study information and allows for a more flexible representation of the data. It's particularly useful when:

- A single study potentially has large number of demographic groups.
- You want to update study information without affecting demographic data.
- You need to analyze demographic data across multiple studies easily.

In the next sections, we'll explore how to establish relationships between these schemas and how to manage them in Extralit.

### Example 2: Establishing Relational Schemas

Let's extend our example to include a third schema for outcome measures:

```python
class OutcomeMeasure(pa.DataFrameModel):
    measure_id: Index[str] = pa.Field(unique=True)
    study_id: Series[str]  # Foreign key to StudyDesign
    demographic_id: Series[str]  # Foreign key to Demographic
    measure_type: Series[str] = pa.Field(isin=['Primary', 'Secondary'])
    value: Series[float] = pa.Field(ge=0)
```

In this schema:

- `study_id` links the outcome to a specific study.
- `demographic_id` optionally links the outcome to a specific demographic group.

This structure allows for complex querying across all three schemas, enabling analysis of outcomes by study and demographic characteristics.

## Converting Schemas to JSON

To use these schemas with Extralit's server, we need to convert them to JSON format. Here's how you can do that:

```python
from os.path import join
target_dir = 'path/to/schemas/'

StudyDesign.to_schema().to_json(join(target_dir, 'study_design_schema.json'))
Demographic.to_schema().to_json(join(target_dir, 'demographic_schema.json'))
OutcomeMeasure.to_schema().to_json(join(target_dir, 'outcome_measure_schema.json'))
```

This code will create three JSON files containing the schema definitions.

## Uploading Schemas to Extralit Server

Once you have your schema JSON files, you can upload them to your Extralit workspace using the command-line interface:

```bash
extralit schemas upload --workspace {WORKSPACE_NAME} --schemas path/to/schemas/
```

Replace `{WORKSPACE_NAME}` with the name of your Extralit workspace, and ensure the path to your schema JSON files is correct.

## Best Practices for Multiple Schemas

1. **Keep It Simple**: Start with the simplest schema structure that accurately represents your data. You can always add complexity later.

2. **Use Meaningful Names**: Choose clear, descriptive names for your schemas and fields.

3. **Establish Clear Relationships**: When using multiple schemas, clearly define how they relate to each other (e.g., through foreign keys).

4. **Avoid Redundancy**: Don't duplicate information across schemas unnecessarily. Use references (foreign keys) instead.

5. **Consider Extraction Efficiency**: Design your schemas to align with how information is typically presented in the papers you're analyzing. This can make the extraction process more straightforward.

6. **Validate Relationships**: Implement cross-schema validation to ensure referential integrity (e.g., every `study_id` in `Demographic` exists in `StudyDesign`).

7. **Document Your Schema Structure**: Maintain clear documentation of how your schemas relate to each other and what each schema represents.

By thoughtfully designing and implementing multiple schemas, you can create a robust, flexible system for extracting and organizing complex information from scientific papers. This approach allows for more nuanced analysis and can significantly improve the quality and usability of your extracted data.

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
