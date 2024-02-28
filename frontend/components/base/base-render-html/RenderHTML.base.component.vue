<template>
	<div v-if="editor" class="editor-container">
		<div v-if="editable" :editor="editor">
			<div class="menubar">
				<button class="menubar__button" @click.prevent="editor.chain().focus().addColumnBefore().run()" 
					:disabled="!editor.can().addColumnBefore()"
				>
					➕ Column
				</button>
				<button class="menubar__button" @click.prevent="editor.chain().focus().deleteColumn().run()" 
					:disabled="!editor.can().deleteColumn()"
				>
					➖ Column
				</button>
				<!-- <button class="menubar__button" @click.prevent="editor.chain().focus().addRowBefore().run()" 
					:disabled="!editor.can().addRowBefore()"
				>
					➕ RowBefore
				</button> -->
				<button class="menubar__button" @click.prevent="editor.chain().focus().addRowAfter().run()" 
					:disabled="!editor.can().addRowAfter()"
				>
					➕ Row
				</button>
				<button class="menubar__button" @click.prevent="editor.chain().focus().deleteRow().run()" 
					:disabled="!editor.can().deleteRow()"
				>
					➖ Row
				</button>
				<button class="menubar__button" @click.prevent="editor.chain().focus().mergeCells().run()" 
					:disabled="!editor.can().mergeCells()"
				>
					Merge Cells
				</button>
				<button class="menubar__button" @click.prevent="editor.chain().focus().splitCell().run()" 
					:disabled="!editor.can().splitCell()"
				>
					Split Cell
				</button>
				<!-- <button class="menubar__button" @click.prevent="editor.chain().focus().mergeOrSplit().run()" 
						:disabled="!editor.can().mergeOrSplit()"
					>
					merge Or Split
				</button> -->
				<button class="menubar__button" @click.prevent="editor.chain().focus().toggleHeaderColumn().run()" 
					:disabled="!editor.can().toggleHeaderColumn()"
				>
					Toggle Index
				</button>
				<button class="menubar__button" @click.prevent="editor.chain().focus().toggleHeaderRow().run()" 
					:disabled="!editor.can().toggleHeaderRow()"
				>
					Toggle Header
				</button>
				<button class="menubar__button" @click.prevent="editor.chain().focus().toggleHeaderCell().run()" 
					:disabled="!editor.can().toggleHeaderCell()"
				>
					Toggle Header Cell
				</button>
				<!-- <button class="menubar__button" @click.prevent="editor.chain().focus().fixTables().run()" 
					:disabled="!editor.can().fixTables()"
				>
					Fix Tables
				</button> -->

				<BaseDropdown :visible="searchReplaceDropdownVisible" class="dropdown" style="width: auto; padding: 0px;">
					<span slot="dropdown-header" @click.prevent="toggleDropdown">
						<BaseButton>
							Find & Replace
						</BaseButton> 
					</span>
					<span slot="dropdown-content" style="padding: 5px;">
						<label for="searchTerm" class="dropdown-label">Search:</label>
						<input id="searchTerm" v-model="searchTerm" type="text" class="dropdown-input" />
	
						<label for="replaceTerm" class="dropdown-label">Replace:</label>
						<input id="replaceTerm" v-model="replaceTerm" type="text" class="dropdown-input" />
	
						<button @click.prevent="replaceAll" class="dropdown-button">Find/Replace All</button>

					</span>
				</BaseDropdown>
			</div>
		</div>

		<editor-content 
			:editor="editor"
			class="editor-content"
			@focus="setFocus(true)"
			@blur="setFocus(false)"
			@contextmenu.prevent="openContextMenu($event, rowIndex, cellIndex)"
		/>
	</div>
</template>

<script>
import Document from '@tiptap/extension-document'
import Gapcursor from '@tiptap/extension-gapcursor'
import Paragraph from '@tiptap/extension-paragraph'
import Table from '@tiptap/extension-table'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import TableRow from '@tiptap/extension-table-row'
import Text from '@tiptap/extension-text'
import History from '@tiptap/extension-history'
import SearchAndReplace from "@sereneinserenade/tiptap-search-and-replace";
import { Editor, EditorContent } from '@tiptap/vue-2'


export default {
	name: "RenderHTML",

	components: {
		EditorContent,
	},

	props: {
		value: {
			type: String,
			required: true,
		},
		placeholder: {
			type: String,
			default: "",
		},
		originalValue: {
			type: String,
			default: "",
		},
		isFocused: {
			type: Boolean,
			default: () => false,
		},
		editable: {
			type: Boolean,
			default: () => false,
		},
	},

	data() {
		return {
			editor: null,
			sanitizedCurrentValue: null,
			currentValue: null,
			searchReplaceDropdownVisible: false,
			searchTerm: "",
			replaceTerm: "",
			contextMenu: {
				visible: false,
				x: 0,
				y: 0,
				rowIndex: null,
				cellIndex: null,
			},
		}
	},

	computed: {
		textIsEdited() {
			return this.originalValue !== this.value;
		},
	},

	watch: {
		isFocused: {
			immediate: true,
			handler(newValue) {
				if (newValue) {
					this.setFocus(true)
				}
			},
		},
		value() {
			if (this.value !== this.currentValue) {
				this.reset();
			}
		},
		editable(value) {
			this.editor.setEditable(value)
		},
	},

	mounted() {
		this.editor = new Editor({
			extensions: [
				Document,
				Paragraph,
				Text,
				History,
				Gapcursor,
				Table.configure({
					resizable: false,
				}),
				TableRow,
				TableHeader,
				TableCell.extend({
					addKeyboardShortcuts() {
						return {
							'Mod-m': () => this.editor.chain().focus().mergeCells().run(),
						}
					}
				}),
				SearchAndReplace.configure({
					searchResultClass: "search-result",
					caseSensitive: true,
					disableRegex: true, 
				}),

			],
			editable: this.editable,
			content: this.value,
			onUpdate: ({ editor }) => {
				this.onChangeText(editor.getHTML());
			},
		})
		this.reset();
	},

	beforeUnmount() {
		this.editor.destroy()
	},

	methods: {
		replaceAll() {
			if (!this.editor.isActive || !this.searchTerm) return;
			this.editor.storage.searchAndReplace.searchTerm = this.searchTerm;
			this.editor.storage.searchAndReplace.replaceTerm = this.replaceTerm;
			
			this.editor.commands.replaceAll();
		},
		toggleDropdown() {
			this.searchReplaceDropdownVisible = !this.searchReplaceDropdownVisible;
		},
		shouldShowBubbleMenu(props) {
			const isCellSelection = props.state.selection?.constructor?.name.includes('CellSelection');
			if (isCellSelection) {
				console.log('shouldShowBubbleMenu', props)
			}
			// // Check if the right mouse button was clicked
			// const isRightClick = props.view.dom.ownerDocument.defaultView.event.button === 2;

			// return isCellSelection && isRightClick && this.editor?.isActive;
			return isCellSelection && this.editor?.isActive
		},
		openContextMenu(event, rowIndex, cellIndex) {
			this.contextMenu.visible = true;
			this.contextMenu.x = event.clientX;
			this.contextMenu.y = event.clientY;
			this.contextMenu.rowIndex = rowIndex;
			this.contextMenu.cellIndex = cellIndex;
		},
		closeContextMenu() {
			this.contextMenu.visible = false;
		},
		reset() {
			this.currentValue = this.value;
			this.sanitizedCurrentValue = " ";
			this.$nextTick(() => {
				this.sanitizedCurrentValue = this.currentValue;
			});
		},
		exitEditionMode() {
			this.editor.blur();
			this.$emit("on-exit-edition-mode");
		},
		onChangeText(value) {
			this.currentValue = value;
			this.$emit("change-text", value);
		},
		setFocus(isFocus) {
			this.$emit("on-change-focus", isFocus);
		},
		pastePlainText(event) {
			if (event.target.isContentEditable) {
				event.preventDefault();
				const text = event.clipboardData?.getData("text/plain") ?? "";
				document.execCommand("insertText", false, text);
			}
		},
		onClickOutside() {
			this.setFocus(false);
		},
	},
}
</script>

<style lang="scss">
.editor-container {
  position: relative;
	flex-flow: column;
	overflow-x: auto;

  &__content {
    padding: 4rem 1rem;
  }

  &__footer {
    text-align: center;
    margin-bottom: 2rem;
  }

  &__source-link {
    display: inline-block;
    text-decoration: none;
    text-transform: uppercase;
    font-weight: bold;
    font-size: 0.8rem;
    background-color: rgba(black, 0.1);
    color: black;
    border-radius: 5px;
    padding: 0.2rem 0.5rem;
  }

	.menubar {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		padding: 5px 5px 0px 0px;
		color: white;
		text-decoration: none;
		overflow-x: visible;

		.menubar__button {
			background-color: transparent;
			border: none;
			border-radius: 0.4rem;
			cursor: pointer;
			height: 1.75rem;
			margin-right: 0.25rem;
			padding: 0.25rem;

			svg {
				fill: currentColor;
				height: 100%;
				width: 100%;
			}

			&:hover,
			&.is-active {
				background-color: #858585;
			}

			&:disabled {
				background-color: #ccc;  // Adjust as needed
				color: #888;  // Adjust as needed
				cursor: not-allowed;
			}
		}

		.dropdown {
			display: flex;
			flex-direction: column;
			width: 200px;
			background-color: #f9f9f9;
			border: 1px solid #ccc;
			padding: 10px;
			border-radius: 4px;
		}

		.dropdown label {
			margin-bottom: 5px;
			font-size: 14px;
			color: #333;
		}

		.dropdown input {
			margin-bottom: 10px;
			padding: 5px;
			border: 1px solid #ccc;
			border-radius: 4px;
		}

		.dropdown button {
			padding: 5px 10px;
			background-color: #4CAF50;
			color: white;
			border: none;
			border-radius: 4px;
			cursor: pointer;
		}

		.dropdown button:hover {
			background-color: #45a049;
		}
	}

	.editor-content {
		min-width: 40vw;
		max-height: 60vh;
		overflow-x: auto;
	}
}

input[type="checkbox"] {
  margin-right: 4px;
}

/* Basic editor styles */
.tiptap {
  margin: 1rem 0;

  > * + * {
    margin-top: 0.75em;
  }

  ul,
  ol {
    padding: 0 1rem;
  }

  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    line-height: 1.1;
  }

  code {
    background-color: rgba(#616161, 0.1);
    color: #616161;
  }

  pre {
    background: #0D0D0D;
    color: #FFF;
    font-family: 'JetBrainsMono', monospace;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;

    code {
      color: inherit;
      padding: 0;
      background: none;
      font-size: 0.8rem;
    }
  }

  img {
    max-width: 100%;
    height: auto;
  }

  blockquote {
    padding-left: 1rem;
    border-left: 2px solid rgba(#0D0D0D, 0.1);
  }

  hr {
    border: none;
    border-top: 2px solid rgba(#0D0D0D, 0.1);
    margin: 2rem 0;
  }

	.search-result {
		background-color: rgba(255, 217, 0, 0.5);

		&-current {
			background-color: rgba(13, 255, 0, 0.5);
		}
	}
}

/* Table-specific styling */
.tiptap {
  table {
    border-collapse: collapse;
    table-layout: fixed;
    margin: 0;
    overflow: hidden;
		overflow-x: auto;

    td,
    th {
      min-width: 1em;
      border: 2px solid #ced4da;
      padding: 3px 5px;
      vertical-align: top;
      box-sizing: border-box;
      position: relative;

      > * {
        margin-bottom: 0;
      }
    }

		td[colspan], th[colspan] {
			vertical-align: middle;
    }

    th {
      font-weight: bold;
      text-align: left;
      background-color: #f1f3f5;
    }

    .selectedCell:after {
      z-index: 2;
      position: absolute;
      content: "";
      left: 0; right: 0; top: 0; bottom: 0;
      background: rgba(200, 200, 255, 0.4);
      pointer-events: none;
    }

    .column-resize-handle {
      position: absolute;
      right: -2px;
      top: 0;
      bottom: -2px;
      width: 4px;
      background-color: #adf;
      pointer-events: none;
    }

    p {
      margin: 0;
    }
  }
}


.resize-cursor {
  cursor: ew-resize;
  cursor: col-resize;
}
</style>