# Import Components

This directory contains Vue.js components for the papers library import workflow.

## Components

### ImportAnalysisTable.vue

A table component for displaying and managing document import analysis results.

**Features:**
- Displays bibliographic data in a tabular format
- Supports both dataframe-based data (from BibTeX parsing) and analysis-based data (from backend analysis)
- Interactive status toggling (Add/Update → Skip/Ignore)
- Color-coded status indicators
- Summary statistics display
- Action buttons for Save, Cancel, and Confirm Import

**Props:**
- `analysisData`: Import analysis results from backend
- `dataframeData`: Direct dataframe data from BibTeX parsing (optional)
- `loading`: Loading state indicator

**Events:**
- `update`: Emitted when user confirms document selections
- `retry`: Emitted when user requests to retry analysis

**Usage:**
```vue
<ImportAnalysisTable
  :analysis-data="analysisData"
  :dataframe-data="bibData.dataframeData"
  :loading="isAnalyzing"
  @update="handleAnalysisUpdate"
  @retry="performImportAnalysis"
/>
```

### Types (types.ts)

TypeScript type definitions for import-related data structures, based on the backend API schemas.

**Key Types:**
- `DataframeData`: Tabular data structure for BibTeX entries
- `ImportAnalysisData`: Backend analysis results
- `BibTexEntry`: Individual bibliography entry
- `ImportStatus`: Document import status enum
- `AnalysisTableRow`: Table row data structure

## Data Flow

1. **Step 1**: User uploads BibTeX file → parsed into `DataframeData`
2. **Step 2**: `DataframeData` displayed in `ImportAnalysisTable` for review
3. **Step 3**: Backend analysis creates `ImportAnalysisData` with status and file matching
4. **Step 4**: User reviews and modifies import decisions
5. **Step 5**: Confirmed documents sent for import processing

## Demo

Visit `/import-demo` to see the component in action with sample data.

## Testing

Run tests with:
```bash
npm test -- --testPathPattern=ImportAnalysisTable.test.js
```

The component includes comprehensive unit tests covering:
- Data rendering and formatting
- User interactions
- Status toggling logic
- Event emission
- Error handling