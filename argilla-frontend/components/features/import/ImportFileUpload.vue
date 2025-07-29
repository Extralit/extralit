<template>
    <div class="import-file-upload">
        <div class="import-file-upload__header">
            <h3 class="import-file-upload__title">Upload Bibliography and PDF Files</h3>
            <p class="import-file-upload__description">
                Upload your bibliography file and PDF folder to import your library
            </p>
        </div>

        <div class="import-file-upload__content">
            <div class="import-file-upload__main">
                <!-- Bibliography Upload Section -->
                <div class="import-file-upload__section">
                    <div class="import-file-upload__section-header">
                        <h3 class="import-file-upload__section-title">Step 1: Upload Your Bibliography File</h3>
                        <p class="import-file-upload__section-description">
                            Import your reference list to begin.<br>
                            We support .bib files exported from reference managers like Zotero, EndNote, or Mendeley.
                        </p>
                    </div>

                    <div class="import-file-upload__dropzone" :class="{
                        'import-file-upload__dropzone--dragover': bibDragOver,
                        'import-file-upload__dropzone--error': bibHasError,
                        'import-file-upload__dropzone--success': bibUploaded,
                    }" @drop="handleBibDrop" @dragover="handleBibDragOver" @dragleave="handleBibDragLeave"
                        @click="triggerBibFileInput">
                        <input ref="bibFileInput" type="file" accept=".bib,.bibtex" style="display: none"
                            @change="handleBibFileSelect" />

                        <div class="import-file-upload__dropzone-content">
                            <BaseIcon :icon-name="getBibDropzoneIcon" class="import-file-upload__dropzone-icon" />
                            <p class="import-file-upload__dropzone-text">
                                {{ getBibDropzoneText }}
                            </p>
                            <p class="import-file-upload__dropzone-subtext">Supported formats: .bib, .bibtex</p>
                        </div>
                    </div>

                    <!-- Bibliography Success Display -->
                    <div v-if="bibUploaded && !bibHasError" class="import-file-upload__upload-success">
                        <BaseIcon icon-name="check" class="import-file-upload__upload-success-icon" />
                        <span class="import-file-upload__upload-success-text">
                            Successfully uploaded {{ bibData.fileName }} ({{ bibData.parsedEntries.length }} entries
                            found)
                        </span>
                    </div>

                    <!-- Bibliography Error Display -->
                    <div v-if="bibHasError" class="import-file-upload__error">
                        <BaseIcon icon-name="danger" class="import-file-upload__error-icon" />
                        <div class="import-file-upload__error-content">
                            <h4>Bibliography Parsing Error</h4>
                            <p>{{ bibErrorMessage }}</p>
                        </div>
                    </div>
                </div>

                <!-- PDF Upload Section -->
                <div class="import-file-upload__section">
                    <div class="import-file-upload__section-header">
                        <h3 class="import-file-upload__section-title">Step 2: Upload Full-Text PDFs</h3>
                        <p class="import-file-upload__section-description">
                            Upload the PDF files that correspond to the references in your .bib file.<br>
                            Extralit will match them automatically for extraction.
                        </p>
                    </div>

                    <div class="import-file-upload__dropzone" :class="{
                        'import-file-upload__dropzone--dragover': pdfDragOver,
                        'import-file-upload__dropzone--error': pdfHasError,
                        'import-file-upload__dropzone--success': pdfUploaded,
                    }" @drop="handlePdfDrop" @dragover="handlePdfDragOver" @dragleave="handlePdfDragLeave"
                        @click="triggerPdfFolderInput">
                        <input ref="pdfFolderInput" type="file" accept=".pdf" multiple webkitdirectory
                            style="display: none" @change="handlePdfFolderSelect" />

                        <div class="import-file-upload__dropzone-content">
                            <BaseIcon :icon-name="getPdfDropzoneIcon" class="import-file-upload__dropzone-icon" />
                            <p class="import-file-upload__dropzone-text">
                                {{ getPdfDropzoneText }}
                            </p>
                            <p class="import-file-upload__dropzone-subtext">
                                ~12 PDF files uploaded
                            </p>
                            <div v-if="!pdfUploaded" class="import-file-upload__dropzone-buttons">
                                <BaseButton class="secondary" @click.stop="triggerPdfFolderInput">
                                    Upload PDF Files
                                </BaseButton>
                            </div>
                        </div>
                    </div>

                    <!-- PDF Processing Progress -->
                    <div v-if="pdfProcessing" class="import-file-upload__progress">
                        <div class="import-file-upload__progress-header">
                            <h4>Processing PDF Files...</h4>
                            <span>{{ pdfProcessedFiles }}/{{ pdfTotalFiles }} files</span>
                        </div>
                        <div class="import-file-upload__progress-bar">
                            <div class="import-file-upload__progress-fill"
                                :style="{ width: `${pdfProgressPercentage}%` }"></div>
                        </div>
                    </div>

                    <!-- PDF Success Display -->
                    <div v-if="pdfUploaded && !pdfHasError && !pdfProcessing"
                        class="import-file-upload__upload-success">
                        <BaseIcon icon-name="check" class="import-file-upload__upload-success-icon" />
                        <span class="import-file-upload__upload-success-text">
                            {{ pdfData.totalFiles }} PDF files uploaded
                        </span>
                    </div>

                    <!-- PDF Error Display -->
                    <div v-if="pdfHasError" class="import-file-upload__error">
                        <BaseIcon icon-name="danger" class="import-file-upload__error-icon" />
                        <div class="import-file-upload__error-content">
                            <h4>PDF Processing Error</h4>
                            <p>{{ pdfErrorMessage }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Summary Sidebar -->
            <div class="import-file-upload__sidebar">
                <h4 class="import-file-upload__sidebar-title">Summary status:</h4>

                <div class="import-file-upload__sidebar-stats">
                    <!-- Bibliography Status -->
                    <div v-if="bibUploaded && !bibHasError" class="import-file-upload__sidebar-stat">
                        <BaseIcon icon-name="document"
                            class="import-file-upload__sidebar-stat-icon import-file-upload__sidebar-stat-icon--bib" />
                        <span class="import-file-upload__sidebar-stat-text">{{ bibData.parsedEntries.length }}
                            references found</span>
                    </div>

                    <!-- PDF Status -->
                    <div v-if="pdfUploaded && !pdfHasError && !pdfProcessing" class="import-file-upload__sidebar-stat">
                        <BaseIcon icon-name="folder"
                            class="import-file-upload__sidebar-stat-icon import-file-upload__sidebar-stat-icon--pdf" />
                        <span class="import-file-upload__sidebar-stat-text">{{ pdfData.totalFiles }} PDF files
                            uploaded</span>
                    </div>

                    <!-- Matching Status -->
                    <div v-if="pdfUploaded && !pdfHasError && !pdfProcessing && pdfData.matchedFiles.length > 0"
                        class="import-file-upload__sidebar-stat">
                        <BaseIcon icon-name="check"
                            class="import-file-upload__sidebar-stat-icon import-file-upload__sidebar-stat-icon--match" />
                        <span class="import-file-upload__sidebar-stat-text">
                            {{ pdfData.matchedFiles.length }} matched, {{ pdfData.unmatchedFiles.length }} mismatch{{
                                pdfData.unmatchedFiles.length === 1 ? '' : 'es' }} detected
                        </span>
                    </div>
                </div>

                <!-- Continue Button -->
                <div v-if="isValid" class="import-file-upload__sidebar-action">
                    <BaseButton class="primary" @click="$emit('continue')">
                        Continue to Import Summary
                    </BaseButton>
                </div>
            </div>

            <!-- Combined Preview Section (only show when both files are uploaded and valid) -->
            <div v-if="bibUploaded && pdfUploaded && !bibHasError && !pdfHasError && !pdfProcessing"
                class="import-file-upload__preview">
                <h4 class="import-file-upload__preview-title">Import Preview</h4>

                <!-- Summary Stats -->
                <div class="import-file-upload__stats">
                    <div class="import-file-upload__stat">
                        <BaseIcon icon-name="document" class="import-file-upload__stat-icon" />
                        <div class="import-file-upload__stat-content">
                            <span class="import-file-upload__stat-value">{{ bibData.parsedEntries.length }}</span>
                            <span class="import-file-upload__stat-label">Bibliography Entries</span>
                        </div>
                    </div>

                    <div class="import-file-upload__stat import-file-upload__stat--success">
                        <BaseIcon icon-name="check" class="import-file-upload__stat-icon" />
                        <div class="import-file-upload__stat-content">
                            <span class="import-file-upload__stat-value">{{ pdfData.matchedFiles.length }}</span>
                            <span class="import-file-upload__stat-label">Matched PDFs</span>
                        </div>
                    </div>

                    <div class="import-file-upload__stat import-file-upload__stat--warning">
                        <BaseIcon icon-name="unavailable" class="import-file-upload__stat-icon" />
                        <div class="import-file-upload__stat-content">
                            <span class="import-file-upload__stat-value">{{ pdfData.unmatchedFiles.length }}</span>
                            <span class="import-file-upload__stat-label">Unmatched PDFs</span>
                        </div>
                    </div>
                </div>

                <!-- Quick Preview Table -->
                <div class="import-file-upload__quick-preview">
                    <h5 class="import-file-upload__quick-preview-title">Sample Matches</h5>
                    <div class="import-file-upload__table-container">
                        <table class="import-file-upload__table">
                            <thead>
                                <tr>
                                    <th>Reference Key</th>
                                    <th>Title</th>
                                    <th>PDF File</th>
                                    <th>Match Type</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="match in previewMatches" :key="match.bibEntry.reference">
                                    <td class="import-file-upload__table-cell--key">{{ match.bibEntry.reference }}</td>
                                    <td class="import-file-upload__table-cell--title">{{ match.bibEntry.title || "N/A"
                                    }}
                                    </td>
                                    <td class="import-file-upload__table-cell--filename">
                                        <BaseIcon icon-name="document" class="import-file-upload__file-icon" />
                                        {{ match.file.name }}
                                    </td>
                                    <td class="import-file-upload__table-cell--match">
                                        <span class="import-file-upload__match-badge"
                                            :class="`import-file-upload__match-badge--${match.matchType}`">
                                            {{ getMatchTypeLabel(match.matchType) }}
                                        </span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div v-if="pdfData.matchedFiles.length > 3" class="import-file-upload__preview-note">
                        <p>Showing first 3 matches. Full details will be available in the next step.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import bibtexParse from "bibtex-parse-js";
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/folder";
import "assets/icons/import";
import "assets/icons/info";
import "assets/icons/unavailable";

export default {
    name: "ImportFileUpload",

    data() {
        return {
            // Bibliography state
            bibDragOver: false,
            bibUploaded: false,
            bibHasError: false,
            bibErrorMessage: "",
            bibData: {
                fileName: "",
                parsedEntries: [],
                dataframeData: null,
                rawContent: "",
            },

            // PDF state
            pdfDragOver: false,
            pdfUploaded: false,
            pdfHasError: false,
            pdfErrorMessage: "",
            pdfProcessing: false,
            pdfProcessedFiles: 0,
            pdfTotalFiles: 0,
            pdfData: {
                matchedFiles: [],
                unmatchedFiles: [],
                totalFiles: 0,
            },
        };
    },

    computed: {
        getBibDropzoneIcon() {
            if (this.bibHasError) return "danger";
            if (this.bibUploaded) return "check";
            return "document";
        },

        getBibDropzoneText() {
            if (this.bibHasError) return "Error parsing bibliography file";
            if (this.bibUploaded) return "Upload .bib File";
            return "Upload .bib File";
        },

        getPdfDropzoneIcon() {
            if (this.pdfHasError) return "danger";
            if (this.pdfUploaded) return "check";
            return "folder";
        },

        getPdfDropzoneText() {
            if (this.pdfHasError) return "Error processing PDF files";
            if (this.pdfUploaded) return "Upload PDF Files";
            return "Upload PDF Files";
        },

        pdfProgressPercentage() {
            if (this.pdfTotalFiles === 0) return 0;
            return Math.round((this.pdfProcessedFiles / this.pdfTotalFiles) * 100);
        },

        previewMatches() {
            return this.pdfData.matchedFiles.slice(0, 3);
        },

        isValid() {
            return (
                this.bibUploaded &&
                this.pdfUploaded &&
                !this.bibHasError &&
                !this.pdfHasError &&
                !this.pdfProcessing &&
                this.bibData.parsedEntries.length > 0 &&
                this.pdfData.matchedFiles.length > 0
            );
        },
    },

    watch: {
        bibData: {
            handler() {
                this.emitBibUpdate();
                if (this.bibUploaded && this.pdfUploaded) {
                    this.performFileMatching();
                }
            },
            deep: true,
        },

        pdfData: {
            handler() {
                this.emitPdfUpdate();
            },
            deep: true,
        },
    },

    methods: {
        // Bibliography methods
        triggerBibFileInput() {
            this.$refs.bibFileInput.click();
        },

        handleBibDragOver(event) {
            event.preventDefault();
            this.bibDragOver = true;
        },

        handleBibDragLeave() {
            this.bibDragOver = false;
        },

        handleBibDrop(event) {
            event.preventDefault();
            this.bibDragOver = false;

            const files = event.dataTransfer.files;
            if (files.length > 0) {
                this.processBibFile(files[0]);
            }
        },

        handleBibFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) {
                this.processBibFile(files[0]);
            }
        },

        async processBibFile(file) {
            // Reset bib state
            this.bibHasError = false;
            this.bibErrorMessage = "";
            this.bibData = {
                fileName: "",
                parsedEntries: [],
                dataframeData: null,
                rawContent: "",
            };

            // Validate file type
            if (!this.isValidBibFileType(file)) {
                this.showBibError("Invalid file type. Please upload a .bib or .bibtex file.");
                return;
            }

            this.bibData.fileName = file.name;

            try {
                // Read file content
                const content = await this.readFileContent(file);
                this.bibData.rawContent = content;

                // Parse BibTeX content
                await this.parseBibTexContent(content);

                if (this.bibData.parsedEntries.length > 0) {
                    this.bibUploaded = true;
                } else {
                    this.showBibError("No valid BibTeX entries found in the file.");
                }
            } catch (error) {
                this.showBibError(`Failed to process file: ${error.message}`);
            }
        },

        isValidBibFileType(file) {
            const validExtensions = [".bib", ".bibtex"];
            const fileName = file.name.toLowerCase();
            return validExtensions.some((ext) => fileName.endsWith(ext));
        },

        readFileContent(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = () => reject(new Error("Failed to read file"));
                reader.readAsText(file, "utf-8");
            });
        },

        async parseBibTexContent(content) {
            try {
                // Parse using bibtex-parse-js
                const parsed = bibtexParse.toJSON(content);

                if (!Array.isArray(parsed) || parsed.length === 0) {
                    throw new Error("No valid BibTeX entries found");
                }

                // Convert to our internal format
                this.bibData.parsedEntries = [];
                const dataframeEntries = [];

                parsed.forEach((entry, index) => {
                    try {
                        const processedEntry = this.processBibTexEntry(entry, index);
                        if (processedEntry) {
                            this.bibData.parsedEntries.push(processedEntry);
                            dataframeEntries.push(this.createDataframeEntry(entry));
                        }
                    } catch (error) {
                        console.warn(`Entry ${index + 1}: ${error.message}`);
                    }
                });

                // Create generic dataframe format
                this.bibData.dataframeData = this.createGenericDataframe(dataframeEntries);
            } catch (error) {
                throw new Error(`BibTeX parsing failed: ${error.message}`);
            }
        },

        processBibTexEntry(entry, index) {
            // Validate required fields
            if (!entry.citationKey) {
                throw new Error("Missing citation key (reference)");
            }

            // Extract and clean fields
            return {
                reference: entry.citationKey,
                type: entry.entryType || "unknown",
                title: this.cleanBibTexField(entry.entryTags?.title),
                authors: this.extractAuthors(entry.entryTags?.author),
                year: this.extractYear(entry.entryTags?.year || entry.entryTags?.date),
                doi: this.cleanBibTexField(entry.entryTags?.doi),
                pmid: this.cleanBibTexField(entry.entryTags?.pmid),
                url: this.cleanBibTexField(entry.entryTags?.url),
                journal: this.cleanBibTexField(entry.entryTags?.journal),
                volume: this.cleanBibTexField(entry.entryTags?.volume),
                pages: this.cleanBibTexField(entry.entryTags?.pages),
                publisher: this.cleanBibTexField(entry.entryTags?.publisher),
                abstract: this.cleanBibTexField(entry.entryTags?.abstract),
                keywords: this.cleanBibTexField(entry.entryTags?.keywords),
                file: this.cleanBibTexField(entry.entryTags?.file),
            };
        },

        createDataframeEntry(entry) {
            // Create a flattened entry preserving all original fields
            const dataframeEntry = {
                reference: entry.citationKey,
                type: entry.entryType || "unknown",
            };

            // Add all entry tags, preserving original field names and values
            if (entry.entryTags) {
                Object.keys(entry.entryTags).forEach((key) => {
                    dataframeEntry[key] = this.cleanBibTexField(entry.entryTags[key]);
                });
            }

            return dataframeEntry;
        },

        createGenericDataframe(entries) {
            if (entries.length === 0) {
                return {
                    schema: { fields: [], primaryKey: ["reference"] },
                    data: [],
                };
            }

            // Detect all unique fields across entries
            const allFields = new Set(["reference", "type"]);
            entries.forEach((entry) => {
                Object.keys(entry).forEach((field) => allFields.add(field));
            });

            // Create schema with type inference
            const fields = Array.from(allFields).map((fieldName) => ({
                name: fieldName,
                type: this.inferFieldType(entries, fieldName),
            }));

            return {
                schema: {
                    fields,
                    primaryKey: ["reference"],
                },
                data: entries,
            };
        },

        inferFieldType(entries, fieldName) {
            // Simple type inference based on field content
            const values = entries.map((entry) => entry[fieldName]).filter((value) => value != null && value !== "");

            if (values.length === 0) return "string";

            // Check if all values are numbers
            if (values.every((value) => !isNaN(value) && !isNaN(parseFloat(value)))) {
                return values.every((value) => Number.isInteger(parseFloat(value))) ? "integer" : "float";
            }

            return "string";
        },

        cleanBibTexField(field) {
            if (!field) return null;

            // Remove BibTeX formatting (braces, quotes)
            let cleaned = field
                .toString()
                .replace(/^\{+|\}+$/g, "") // Remove outer braces
                .replace(/^"+|"+$/g, "") // Remove outer quotes
                .trim();

            return cleaned || null;
        },

        extractAuthors(authorField) {
            if (!authorField) return null;

            const cleaned = this.cleanBibTexField(authorField);
            if (!cleaned) return null;

            // Handle different author separators
            const authors = cleaned
                .split(/\s+and\s+|\s*,\s*(?=[A-Z])/i)
                .map((author) => author.trim())
                .filter((author) => author.length > 0);

            return authors.length > 0 ? authors.join(", ") : null;
        },

        extractYear(yearField) {
            if (!yearField) return null;

            const cleaned = this.cleanBibTexField(yearField);
            if (!cleaned) return null;

            // Extract 4-digit year from various formats
            const yearMatch = cleaned.match(/\b(19|20)\d{2}\b/);
            return yearMatch ? yearMatch[0] : null;
        },

        showBibError(message) {
            this.bibHasError = true;
            this.bibErrorMessage = message;
            this.bibUploaded = false;
        },

        // PDF methods
        triggerPdfFolderInput() {
            this.$refs.pdfFolderInput.click();
        },

        handlePdfDragOver(event) {
            event.preventDefault();
            this.pdfDragOver = true;
        },

        handlePdfDragLeave() {
            this.pdfDragOver = false;
        },

        handlePdfDrop(event) {
            event.preventDefault();
            this.pdfDragOver = false;

            const files = Array.from(event.dataTransfer.files);
            this.processPdfFiles(files);
        },

        handlePdfFolderSelect(event) {
            const files = Array.from(event.target.files);
            this.processPdfFiles(files);
        },

        async processPdfFiles(files) {
            // Reset PDF state
            this.pdfHasError = false;
            this.pdfErrorMessage = "";
            this.pdfData = {
                matchedFiles: [],
                unmatchedFiles: [],
                totalFiles: 0,
            };
            this.pdfProcessedFiles = 0;

            // Filter for PDF files only
            const pdfFiles = files.filter(file => this.isValidPdfFile(file));

            if (pdfFiles.length === 0) {
                this.showPdfError("No valid PDF files found. Please select a folder containing PDF files.");
                return;
            }

            this.pdfTotalFiles = pdfFiles.length;
            this.pdfProcessing = true;

            try {
                // Process files with validation
                const validFiles = [];
                for (const file of pdfFiles) {
                    await this.processPdfFile(file);
                    validFiles.push(file);
                    this.pdfProcessedFiles++;
                }

                this.pdfData.totalFiles = validFiles.length;

                // Perform file matching with bibliography entries
                this.performFileMatching(validFiles);

                this.pdfProcessing = false;
                this.pdfUploaded = true;
            } catch (error) {
                this.pdfProcessing = false;
                this.showPdfError(`Failed to process PDF files: ${error.message}`);
            }
        },

        async processPdfFile(file) {
            // Validate file size (max 50MB per file)
            const maxSize = 50 * 1024 * 1024; // 50MB
            if (file.size > maxSize) {
                throw new Error(`File ${file.name} is too large (max 50MB)`);
            }

            // Basic PDF validation (check file signature)
            if (!await this.validatePdfFile(file)) {
                throw new Error(`File ${file.name} is not a valid PDF`);
            }

            // Simulate processing delay for UX
            await new Promise(resolve => setTimeout(resolve, 50));
        },

        isValidPdfFile(file) {
            return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
        },

        async validatePdfFile(file) {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const arrayBuffer = e.target.result;
                    const uint8Array = new Uint8Array(arrayBuffer.slice(0, 4));

                    // Check PDF signature (%PDF)
                    const pdfSignature = [0x25, 0x50, 0x44, 0x46]; // %PDF
                    const isValidPdf = pdfSignature.every((byte, index) => uint8Array[index] === byte);
                    resolve(isValidPdf);
                };
                reader.onerror = () => resolve(false);
                reader.readAsArrayBuffer(file.slice(0, 4));
            });
        },

        performFileMatching(uploadedFiles = null) {
            const filesToMatch = uploadedFiles || this.pdfData.matchedFiles.concat(this.pdfData.unmatchedFiles).map(item => item.file || item);

            if (!this.bibData.parsedEntries || this.bibData.parsedEntries.length === 0 || filesToMatch.length === 0) {
                return;
            }

            this.pdfData.matchedFiles = [];
            this.pdfData.unmatchedFiles = [];

            for (const file of filesToMatch) {
                const match = this.findBestMatch(file);

                if (match) {
                    this.pdfData.matchedFiles.push({
                        file,
                        bibEntry: match.entry,
                        matchType: match.type,
                        confidence: match.confidence,
                    });
                } else {
                    this.pdfData.unmatchedFiles.push(file);
                }
            }

            // Sort matched files by confidence (highest first)
            this.pdfData.matchedFiles.sort((a, b) => b.confidence - a.confidence);
        },

        findBestMatch(file) {
            const fileName = file.name.toLowerCase().replace(/\.pdf$/, "");
            let bestMatch = null;
            let bestConfidence = 0;

            for (const entry of this.bibData.parsedEntries) {
                const matches = [
                    // Exact reference key match
                    this.checkExactMatch(fileName, entry.reference),
                    // Partial reference key match
                    this.checkPartialMatch(fileName, entry.reference),
                    // File field match (Zotero exports)
                    this.checkFileFieldMatch(fileName, entry.file),
                    // Fuzzy title match
                    this.checkTitleMatch(fileName, entry.title),
                ].filter(Boolean);

                if (matches.length > 0) {
                    const bestFileMatch = matches.reduce((best, current) =>
                        current.confidence > best.confidence ? current : best
                    );

                    if (bestFileMatch.confidence > bestConfidence) {
                        bestMatch = {
                            entry,
                            type: bestFileMatch.type,
                            confidence: bestFileMatch.confidence,
                        };
                        bestConfidence = bestFileMatch.confidence;
                    }
                }
            }

            // Only return matches with reasonable confidence
            return bestConfidence >= 0.6 ? bestMatch : null;
        },

        checkExactMatch(fileName, reference) {
            if (!reference) return null;

            const refKey = reference.toLowerCase();
            if (fileName === refKey) {
                return { type: "exact", confidence: 1.0 };
            }
            return null;
        },

        checkPartialMatch(fileName, reference) {
            if (!reference) return null;

            const refKey = reference.toLowerCase();
            if (fileName.includes(refKey) || refKey.includes(fileName)) {
                const similarity = this.calculateStringSimilarity(fileName, refKey);
                if (similarity >= 0.7) {
                    return { type: "partial", confidence: similarity };
                }
            }
            return null;
        },

        checkFileFieldMatch(fileName, fileField) {
            if (!fileField) return null;

            // Parse Zotero file field format: "PDF:files/2/filename.pdf:application/pdf"
            const filePaths = fileField.split(";").map(f => f.trim());

            for (const filePath of filePaths) {
                const parts = filePath.split(":");
                if (parts.length >= 2) {
                    const path = parts[1].toLowerCase();
                    const pathFileName = path.split("/").pop().replace(/\.pdf$/, "");

                    if (fileName === pathFileName) {
                        return { type: "file_field", confidence: 0.95 };
                    }

                    const similarity = this.calculateStringSimilarity(fileName, pathFileName);
                    if (similarity >= 0.8) {
                        return { type: "file_field", confidence: similarity };
                    }
                }
            }
            return null;
        },

        checkTitleMatch(fileName, title) {
            if (!title) return null;

            // Clean and normalize title for comparison
            const cleanTitle = title
                .toLowerCase()
                .replace(/[^\w\s]/g, " ")
                .replace(/\s+/g, " ")
                .trim();

            const cleanFileName = fileName
                .replace(/[^\w\s]/g, " ")
                .replace(/\s+/g, " ")
                .trim();

            // Check if filename contains significant words from title
            const titleWords = cleanTitle.split(" ").filter(word => word.length > 3);
            const fileWords = cleanFileName.split(" ");

            let matchedWords = 0;
            for (const titleWord of titleWords) {
                if (fileWords.some(fileWord =>
                    fileWord.includes(titleWord) || titleWord.includes(fileWord)
                )) {
                    matchedWords++;
                }
            }

            if (titleWords.length > 0) {
                const confidence = matchedWords / titleWords.length;
                if (confidence >= 0.6) {
                    return { type: "title", confidence: confidence * 0.8 }; // Lower confidence for title matches
                }
            }

            return null;
        },

        calculateStringSimilarity(str1, str2) {
            // Simple Levenshtein distance-based similarity
            const longer = str1.length > str2.length ? str1 : str2;
            const shorter = str1.length > str2.length ? str2 : str1;

            if (longer.length === 0) return 1.0;

            const distance = this.levenshteinDistance(longer, shorter);
            return (longer.length - distance) / longer.length;
        },

        levenshteinDistance(str1, str2) {
            const matrix = [];

            for (let i = 0; i <= str2.length; i++) {
                matrix[i] = [i];
            }

            for (let j = 0; j <= str1.length; j++) {
                matrix[0][j] = j;
            }

            for (let i = 1; i <= str2.length; i++) {
                for (let j = 1; j <= str1.length; j++) {
                    if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                        matrix[i][j] = matrix[i - 1][j - 1];
                    } else {
                        matrix[i][j] = Math.min(
                            matrix[i - 1][j - 1] + 1,
                            matrix[i][j - 1] + 1,
                            matrix[i - 1][j] + 1
                        );
                    }
                }
            }

            return matrix[str2.length][str1.length];
        },

        getMatchTypeLabel(matchType) {
            const labels = {
                exact: "Exact",
                partial: "Partial",
                file_field: "File Path",
                title: "Title",
            };
            return labels[matchType] || "Unknown";
        },

        showPdfError(message) {
            this.pdfHasError = true;
            this.pdfErrorMessage = message;
            this.pdfUploaded = false;
        },

        // Event emitters
        emitBibUpdate() {
            this.$emit("bib-update", {
                isValid: this.bibUploaded && !this.bibHasError && this.bibData.parsedEntries.length > 0,
                fileName: this.bibData.fileName,
                parsedEntries: this.bibData.parsedEntries,
                dataframeData: this.bibData.dataframeData,
                rawContent: this.bibData.rawContent,
            });
        },

        emitPdfUpdate() {
            this.$emit("pdf-update", {
                isValid: this.pdfUploaded && !this.pdfHasError && this.pdfData.matchedFiles.length > 0,
                matchedFiles: this.pdfData.matchedFiles,
                unmatchedFiles: this.pdfData.unmatchedFiles,
                totalFiles: this.pdfData.totalFiles,
                hasError: this.pdfHasError,
                errorMessage: this.pdfErrorMessage,
            });
        },

        // Public methods for parent components
        reset() {
            // Reset bibliography state
            this.bibDragOver = false;
            this.bibUploaded = false;
            this.bibHasError = false;
            this.bibErrorMessage = "";
            this.bibData = {
                fileName: "",
                parsedEntries: [],
                dataframeData: null,
                rawContent: "",
            };

            // Reset PDF state
            this.pdfDragOver = false;
            this.pdfUploaded = false;
            this.pdfHasError = false;
            this.pdfErrorMessage = "";
            this.pdfProcessing = false;
            this.pdfProcessedFiles = 0;
            this.pdfTotalFiles = 0;
            this.pdfData = {
                matchedFiles: [],
                unmatchedFiles: [],
                totalFiles: 0,
            };

            this.emitBibUpdate();
            this.emitPdfUpdate();
        },
    },
};
</script>
<style lang="scss" scoped>
.import-file-upload {
    padding: $base-space * 3;

    &__header {
        text-align: center;
        margin-bottom: $base-space * 3;
    }

    &__title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: $base-space;
        color: var(--fg-primary);
    }

    &__description {
        color: var(--fg-secondary);
        margin-bottom: 0;
    }

    &__content {
        display: flex;
        gap: $base-space * 3;

        @media (max-width: 768px) {
            flex-direction: column;
        }
    }

    &__main {
        flex: 2;
        display: flex;
        flex-direction: column;
        gap: $base-space * 3;
    }

    &__sidebar {
        flex: 1;
        background: var(--bg-accent-grey-1);
        border: 1px solid var(--border-field);
        border-radius: $border-radius-m;
        padding: $base-space * 2;
        height: fit-content;
        position: sticky;
        top: $base-space * 2;
    }

    &__section {
        display: flex;
        flex-direction: column;
        gap: $base-space * 2;
    }

    &__section-header {
        margin-bottom: $base-space * 2;
    }

    &__section-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: $base-space;
        color: var(--fg-primary);
    }

    &__section-icon {
        font-size: 1.2rem;
        color: var(--fg-secondary);
    }

    &__section-description {
        color: var(--fg-secondary);
        font-size: 0.9rem;
        margin-bottom: 0;
        line-height: 1.4;
    }

    &__dropzone {
        border: 2px dashed var(--border-field);
        border-radius: $border-radius-m;
        padding: $base-space * 4 $base-space * 3;
        text-align: center;
        cursor: pointer;
        transition: $swift-ease-out;
        background: var(--bg-accent-grey-1);

        &:hover {
            border-color: var(--bg-action);
            background: var(--bg-accent-grey-2);
        }

        &--dragover {
            border-color: var(--bg-action);
            background: var(--bg-accent-grey-2);
            transform: scale(1.02);
        }

        &--error {
            border-color: var(--color-danger);
            background: var(--bg-banner-error);
        }

        &--success {
            border-color: var(--color-success);
            background: var(--bg-solid-grey-2);
        }
    }

    &__dropzone-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: $base-space;
    }

    &__dropzone-icon {
        font-size: 3rem;
        color: var(--fg-secondary);
    }

    &__dropzone-text {
        font-size: 1.1rem;
        font-weight: 500;
        color: var(--fg-primary);
        margin: 0;
    }

    &__dropzone-subtext {
        font-size: 0.9rem;
        color: var(--fg-secondary);
        margin: 0;
    }

    &__dropzone-buttons {
        display: flex;
        gap: $base-space;
        margin-top: $base-space;
    }

    &__progress {
        padding: $base-space * 2;
        background: var(--bg-accent-grey-2);
        border-radius: $border-radius;
        border: 1px solid var(--border-field);
    }

    &__progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: $base-space;

        h4 {
            margin: 0;
            font-size: 1rem;
            color: var(--fg-primary);
        }

        span {
            font-size: 0.9rem;
            color: var(--fg-secondary);
        }
    }

    &__progress-bar {
        width: 100%;
        height: 8px;
        background: var(--bg-accent-grey-3);
        border-radius: $border-radius-s;
        overflow: hidden;
    }

    &__progress-fill {
        height: 100%;
        background: var(--bg-action);
        border-radius: $border-radius-s;
        transition: width 0.3s ease;
    }

    &__success {
        display: flex;
        align-items: center;
        gap: $base-space;
        padding: $base-space * 2;
        background: var(--bg-solid-grey-2);
        border: 1px solid var(--color-success);
        border-radius: $border-radius;
    }

    &__success-icon {
        color: var(--color-success);
        font-size: 1.2rem;
    }

    &__success-content h4 {
        margin: 0 0 $base-space / 2 0;
        color: var(--color-success);
        font-size: 1rem;
    }

    &__success-content p {
        margin: 0;
        color: var(--fg-primary);
    }

    &__error {
        display: flex;
        align-items: flex-start;
        gap: $base-space;
        padding: $base-space * 2;
        background: var(--bg-banner-error);
        border: 1px solid var(--color-danger);
        border-radius: $border-radius;
    }

    &__error-icon {
        color: var(--color-danger);
        font-size: 1.2rem;
        margin-top: 0.1rem;
    }

    &__error-content h4 {
        margin: 0 0 $base-space 0;
        color: var(--color-danger);
        font-size: 1rem;
    }

    &__error-content p {
        margin: 0;
        color: var(--fg-primary);
    }

    &__upload-success {
        display: flex;
        align-items: center;
        gap: $base-space;
        padding: $base-space;
        background: var(--bg-solid-grey-2);
        border: 1px solid var(--color-success);
        border-radius: $border-radius;
        margin-top: $base-space;
    }

    &__upload-success-icon {
        color: var(--color-success);
        font-size: 1rem;
        flex-shrink: 0;
    }

    &__upload-success-text {
        color: var(--fg-primary);
        font-size: 0.9rem;
        font-weight: 500;
    }

    &__sidebar-title {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: $base-space * 2;
        color: var(--fg-primary);
    }

    &__sidebar-stats {
        display: flex;
        flex-direction: column;
        gap: $base-space * 2;
        margin-bottom: $base-space * 3;
    }

    &__sidebar-stat {
        display: flex;
        align-items: flex-start;
        gap: $base-space;
    }

    &__sidebar-stat-icon {
        font-size: 1.2rem;
        margin-top: 0.1rem;
        flex-shrink: 0;

        &--bib {
            color: var(--color-danger);
        }

        &--pdf {
            color: var(--fg-secondary);
        }

        &--match {
            color: var(--color-success);
        }
    }

    &__sidebar-stat-text {
        color: var(--fg-primary);
        font-size: 0.9rem;
        line-height: 1.4;
    }

    &__sidebar-action {
        margin-top: auto;
        padding-top: $base-space * 2;
        border-top: 1px solid var(--border-field);
    }

    &__preview-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: $base-space * 2;
        color: var(--fg-primary);
        text-align: center;
    }

    &__stats {
        display: flex;
        justify-content: center;
        gap: $base-space * 2;
        margin-bottom: $base-space * 3;
        flex-wrap: wrap;
    }

    &__stat {
        display: flex;
        align-items: center;
        gap: $base-space;
        padding: $base-space;
        background: var(--bg-accent-grey-2);
        border-radius: $border-radius;
        border: 1px solid var(--border-field);

        &--success {
            border-color: var(--color-success);
            background: var(--bg-solid-grey-2);
        }

        &--warning {
            border-color: var(--color-warning);
            background: var(--bg-banner-warning);
        }
    }

    &__stat-icon {
        font-size: 1.2rem;
        color: var(--fg-secondary);

        .import-file-upload__stat--success & {
            color: var(--color-success);
        }

        .import-file-upload__stat--warning & {
            color: var(--color-warning);
        }
    }

    &__stat-content {
        display: flex;
        flex-direction: column;
        gap: $base-space / 4;
    }

    &__stat-value {
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--fg-primary);
    }

    &__stat-label {
        font-size: 0.9rem;
        color: var(--fg-secondary);
    }

    &__quick-preview {
        margin-top: $base-space * 2;
    }

    &__quick-preview-title {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: $base-space * 2;
        color: var(--fg-primary);
    }

    &__table-container {
        overflow-x: auto;
        border: 1px solid var(--border-field);
        border-radius: $border-radius;
    }

    &__table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;

        th {
            background: var(--bg-accent-grey-2);
            padding: $base-space;
            text-align: left;
            font-weight: 600;
            color: var(--fg-primary);
            border-bottom: 1px solid var(--border-field);
        }

        td {
            padding: $base-space;
            border-bottom: 1px solid var(--border-field);
            color: var(--fg-primary);
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover {
            background: var(--bg-accent-grey-3);
        }
    }

    &__table-cell {
        &--key {
            font-family: $quaternary-font-family;
            font-weight: 600;
            color: var(--bg-action);
        }

        &--title {
            font-weight: 500;
            max-width: 250px;
        }

        &--filename {
            display: flex;
            align-items: center;
            gap: $base-space / 2;
            font-weight: 500;
            max-width: 200px;
        }

        &--match {
            text-align: center;
        }
    }

    &__file-icon {
        color: var(--color-danger);
        font-size: 1rem;
        flex-shrink: 0;
    }

    &__match-badge {
        display: inline-block;
        padding: $base-space / 4 $base-space / 2;
        border-radius: $border-radius-s;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;

        &--exact {
            background: var(--color-success);
            color: white;
        }

        &--partial {
            background: var(--bg-action);
            color: white;
        }

        &--file_field {
            background: var(--bg-action);
            color: white;
        }

        &--title {
            background: var(--color-warning);
            color: white;
        }
    }

    &__preview-note {
        margin-top: $base-space * 2;
        text-align: center;

        p {
            margin: 0;
            font-size: 0.9rem;
            color: var(--fg-secondary);
            font-style: italic;
        }
    }
}
</style>