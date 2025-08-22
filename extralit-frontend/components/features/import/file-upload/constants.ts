/**
 * Constants for file upload components
 */

export const FILE_UPLOAD_CONSTANTS = {
  MAX_PDF_SIZE: 200 * 1024 * 1024, // 200MB
  ACCEPTED_PDF_EXTENSIONS: [".pdf"] as string[],
  ACCEPTED_BIB_EXTENSIONS: [".bib", ".bibtex", ".csv"] as string[],
} as const;