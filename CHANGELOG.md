# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-12-25

#### TableField and TableQuestion Support (#114)

**New Features:**
- Added support for `TableField` type in dataset field configuration
  - Table field type now available in field type dropdown
  - Users can map JSON table types to TableField
  - Added `isTableType` getter for type checking

- Added support for `TableQuestion` type in dataset question configuration
  - Table question type now available in question type dropdown
  - Dynamic column management (add/remove columns)
  - Each column configurable with name, title, and description
  - Default initialization with 2 sample columns
  - Validation ensures at least one column is defined

**Components:**
- New `DatasetConfigurationTableQuestion.vue` component for table question UI
  - Column list with inline editing
  - Add/remove column buttons
  - Input validation with error display
  - Focus event handling for better UX

**Backend Changes:**
- `FieldCreation.ts`: Added table field type support
  - Added to `availableFieldTypes` array
  - Updated `FieldCreationTypes` type
  - Added `isTableType` getter method

- `QuestionCreation.ts`: Added table question type support
  - Added to `availableQuestionTypes` array
  - Imported and integrated `TableQuestionAnswer`
  - Added `isTableType` getter method
  - Implemented `createInitialAnswers()` for table questions
  - Added validation requiring at least one column

- `Subset.ts`: Added default settings initialization
  - Auto-creates 2 default columns when table question added
  - Sets `use_table: true` flag

**UI Updates:**
- `DatasetConfigurationQuestion.vue`: Added conditional rendering for table questions
- Added i18n translations for table question UI elements

**Tests:**
- Added unit tests for table question initialization
- Added unit tests for table question validation
- Added comprehensive Vue component tests for `DatasetConfigurationTableQuestion`
  - Component rendering tests
  - Column management tests (add/remove/update)
  - Validation behavior tests
  - Event emission tests

**Files Modified:**
- `extralit-frontend/v1/domain/entities/hub/FieldCreation.ts`
- `extralit-frontend/v1/domain/entities/hub/QuestionCreation.ts`
- `extralit-frontend/v1/domain/entities/hub/Subset.ts`
- `extralit-frontend/components/features/dataset-creation/configuration/questions/DatasetConfigurationQuestion.vue`
- `extralit-frontend/translation/en.js`
- `extralit-frontend/v1/domain/entities/hub/DatasetCreation.test.ts`

**Files Added:**
- `extralit-frontend/components/features/dataset-creation/configuration/questions/DatasetConfigurationTableQuestion.vue`
- `extralit-frontend/components/features/dataset-creation/configuration/questions/DatasetConfigurationTableQuestion.test.ts`

**Impact:**
- Users can now create and configure table fields in dataset schemas
- Users can now create table questions for table annotation workflows
- No breaking changes to existing question or field types
- Follows existing architectural patterns for extensibility

**Related Issue:** #114
