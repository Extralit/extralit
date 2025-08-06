# Requirements Document

## Introduction

The Import History Sidebar feature enhances the home page user experience by displaying recent ImportHistory records in the sidebar and providing a new route to view import configurations using existing DatasetConfiguration components. This feature builds on the existing papers-library-importer functionality to create a seamless workflow from import history to dataset configuration.

The feature replaces the current example datasets section in the home page sidebar with a list of recent ImportHistory records, allowing users to quickly access and create a new configurable annotation datasets from the imported data. When users click on an import history item, they navigate to a new route that displays the DatasetConfiguration component with the ImportHistory data instead of HuggingFace Hub data.

## Requirements

### Requirement 1

**User Story:** As a researcher, I want to see my recent ImportHistory records in the home page sidebar, so that I can quickly access and work with my recently imported data.

#### Acceptance Criteria

1. WHEN I visit the home page THEN the system SHALL display a "Recent Imports" section in the sidebar instead of the example datasets section
2. WHEN the Recent Imports section loads THEN the system SHALL fetch and display the 5 most recent ImportHistory records for the selected workspace
3. WHEN displaying ImportHistory records THEN the system SHALL show the filename, import date, and a summary of imported items count
4. WHEN no ImportHistory records exist THEN the system SHALL display a message encouraging users to import documents
5. WHEN I select a different workspace THEN the system SHALL update the Recent Imports list to show imports for that workspace
6. WHEN ImportHistory records are loading THEN the system SHALL display a loading indicator

### Requirement 2

**User Story:** As a researcher, I want to click on an ImportHistory record in the sidebar, so that I can navigate to a configuration page to work with that imported data.

#### Acceptance Criteria

1. WHEN I click on an ImportHistory record THEN the system SHALL navigate to the route `new/import/{import_id}`
2. WHEN navigating to the import configuration route THEN the system SHALL pass the ImportHistory ID as a route parameter
3. WHEN the import configuration page loads THEN the system SHALL fetch the ImportHistory data using the provided ID
4. WHEN ImportHistory data is successfully loaded THEN the system SHALL display the DatasetConfiguration component
5. IF the ImportHistory record doesn't exist or I don't have access THEN the system SHALL display an appropriate error message
6. WHEN the import configuration page loads THEN the system SHALL display a breadcrumb showing "Home > Import Configuration > {filename}"

### Requirement 3

**User Story:** As a researcher, I want to see the DatasetConfiguration component populated with my ImportHistory data instead of HuggingFace Hub data, so that I can configure datasets from my imported documents.

#### Acceptance Criteria

1. WHEN the DatasetConfiguration component loads with ImportHistory data THEN the system SHALL display the imported tabular data in the preview section instead of the HuggingFace Hub iframe
2. WHEN displaying ImportHistory data THEN the system SHALL show the data in a table format with columns from the original import
3. WHEN ImportHistory data contains multiple records THEN the system SHALL display them in a paginated table with sorting and filtering capabilities
4. WHEN the first record exists in ImportHistory data THEN the system SHALL use it to populate the fields section of the DatasetConfiguration
5. WHEN ImportHistory data is being processed THEN the system SHALL display loading indicators in the appropriate sections
6. WHEN ImportHistory data fails to load THEN the system SHALL display error messages and provide options to retry or return to home
7. WHEN displaying ImportHistory data THEN the system SHALL show a preview of the annotation dataset using the first row from ImportHistoryDetailsResponse.data.data
8. WHEN ImportHistory data is loaded THEN the system SHALL allow mapping columns from the ImportHistory data to create record Fields, similar to HuggingFace Dataset import functionality

### Requirement 4

**User Story:** As a researcher, I want the ImportHistory-based DatasetConfiguration to integrate seamlessly with existing dataset creation workflows, so that I can create datasets from my imported data using familiar interfaces.

#### Acceptance Criteria

1. WHEN using DatasetConfiguration with ImportHistory data THEN the system SHALL support all existing configuration options (field mapping, question creation, etc.)
2. WHEN I configure fields and questions THEN the system SHALL apply them to the ImportHistory data structure
3. WHEN I save the dataset configuration THEN the system SHALL create a new dataset using the ImportHistory data and my configuration settings
4. WHEN the dataset is created successfully THEN the system SHALL navigate to the dataset view or provide options to continue working with the dataset
5. WHEN configuration changes are made THEN the system SHALL validate them against the ImportHistory data structure
6. WHEN I navigate away from the configuration page THEN the system SHALL prompt to save unsaved changes if any exist
7. WHEN Records are created from ImportHistory data THEN the system SHALL populate each record.metadata.reference field with the value from ImportHistoryDetailsResponse.data.data[]["reference"]

### Requirement 5

**User Story:** As a researcher, I want the Recent Imports sidebar to be responsive and performant, so that it doesn't slow down my workflow or interfere with other home page functionality.

#### Acceptance Criteria

1. WHEN the Recent Imports section loads THEN the system SHALL fetch data asynchronously without blocking other page functionality
2. WHEN ImportHistory records are updated THEN the system SHALL refresh the Recent Imports list automatically
3. WHEN I interact with Recent Imports THEN the system SHALL provide immediate visual feedback (hover states, loading indicators)
4. WHEN the sidebar is displayed on mobile devices THEN the system SHALL adapt the layout appropriately for smaller screens
5. WHEN there are many ImportHistory records THEN the system SHALL only load the most recent 5 to maintain performance
6. WHEN API requests fail THEN the system SHALL handle errors gracefully and provide retry options

### Requirement 6

**User Story:** As a researcher, I want to access the full import history and import new documents from the Recent Imports sidebar, so that I can manage all my imports from one convenient location.

#### Acceptance Criteria

1. WHEN I view the Recent Imports sidebar THEN the system SHALL display a "View All Imports" button below the recent imports list
2. WHEN I click "View All Imports" THEN the system SHALL open the ImportHistoryList modal showing the complete import history for the workspace
3. WHEN I view the Recent Imports sidebar THEN the system SHALL display an "Import Documents" button
4. WHEN I click "Import Documents" THEN the system SHALL open the ImportModal for uploading new documents
5. WHEN the ImportHistoryList modal is open THEN the system SHALL support all existing functionality (filtering, pagination, viewing details)
6. WHEN I close the ImportHistoryList modal THEN the system SHALL return to the home page with the Recent Imports sidebar still visible

### Requirement 7

**User Story:** As a researcher, I want proper navigation and routing for the import configuration feature, so that I can bookmark, share, and navigate to specific import configurations easily.

#### Acceptance Criteria

1. WHEN I access the route `new/import/{import_id}` THEN the system SHALL validate the import_id parameter and load the corresponding ImportHistory record
2. WHEN the import_id is invalid or doesn't exist THEN the system SHALL redirect to the home page with an appropriate error message
3. WHEN I bookmark the import configuration URL THEN the system SHALL allow direct access to that specific import configuration
4. WHEN I use browser back/forward buttons THEN the system SHALL navigate correctly between the home page and import configuration
5. WHEN I refresh the import configuration page THEN the system SHALL reload the ImportHistory data and maintain the current state
6. WHEN I navigate to the import configuration route without proper authentication THEN the system SHALL redirect to the login page