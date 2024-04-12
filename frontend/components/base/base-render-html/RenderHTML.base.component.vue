<template>
	<div v-if="editor" class="editor-container">
		<div v-if="editable" :editor="editor">
			<div class="menubar">
				<BaseDropdown 
					class="dropdown" 
					:visible="dropdownAddVisible" 
					@mouseover.native="dropdownAddVisible = true"
					@mouseleave.native="dropdownAddVisible = false"
				>
					<span slot="dropdown-header">
						<BaseButton 
							slot="dropdown-header" 
							class="dropdown-header" 
							@click.prevent="dropdownAddVisible = !dropdownAddVisible"
						>
							Add
							<svgicon name="chevron-down" width="8" height="8" />
						</BaseButton>
					</span>
					<span slot="dropdown-content">
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().addColumnBefore().run()"
							:disabled="!editor.can().addColumnBefore()">
							➕ Column ←
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().addColumnAfter().run()"
							:disabled="!editor.can().addColumnAfter()">
							➕ Column →
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().addRowBefore().run()" 
							:disabled="!editor.can().addRowBefore()">
							➕ Row ↑
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().addRowAfter().run()"
							:disabled="!editor.can().addRowAfter()">
							➕ Row ↓
						</BaseButton>
					</span>
				</BaseDropdown>

				<BaseDropdown 
					class="dropdown" 
					:visible="dropdownRemoveVisible"
					@mouseover.native="dropdownRemoveVisible = true"
					@mouseleave.native="dropdownRemoveVisible = false"
				>
					<span slot="dropdown-header">
						<BaseButton slot="dropdown-header" class="dropdown-header" @click.prevent="dropdownRemoveVisible = !dropdownRemoveVisible">
							Remove
							<svgicon name="chevron-down" width="8" height="8" />
						</BaseButton>
					</span>
					<span slot="dropdown-content">
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().deleteColumn().run()"
							:disabled="!editor.can().deleteColumn()">
							➖ Column
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().deleteRow().run()"
							:disabled="!editor.can().deleteRow()">
							➖ Row
						</BaseButton>
					</span>
				</BaseDropdown>

				<BaseDropdown 
					class="dropdown" 
					:visible="dropdownToggleVisible"
					@mouseover.native="dropdownToggleVisible = true"
					@mouseleave.native="dropdownToggleVisible = false"
				>
					<span slot="dropdown-header">
						<BaseButton slot="dropdown-header" class="dropdown-header" @click.prevent="dropdownToggleVisible = !dropdownToggleVisible">
							Toggle selected
							<svgicon name="chevron-down" width="8" height="8" />
						</BaseButton>
					</span>
					<span slot="dropdown-content">
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().toggleHeaderColumn().run()"
							:disabled="!editor.can().toggleHeaderColumn()">
							As Row Header
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().toggleHeaderRow().run()"
							:disabled="!editor.can().toggleHeaderRow()">
							As Column Header
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().toggleHeaderCell().run()"
							:disabled="!editor.can().toggleHeaderCell()">
							As Selected as Header
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().mergeCells().run()"
							:disabled="!editor.can().mergeCells()">
							Merge Cells
						</BaseButton>
						<BaseButton class="menubar__button" @click.prevent="editor.chain().focus().splitCell().run()"
							:disabled="!editor.can().splitCell()">
							Split Cell
						</BaseButton>
						<!-- <BaseButton class="menubar__button" @click.prevent="splitRow" :disabled="!editor.can().mergeCells()">
							Split Row
						</BaseButton> -->
					</span>
				</BaseDropdown>

				<BaseDropdown class="dropdown" :visible="dropdownSearchReplaceVisible" >
					<span slot="dropdown-header">
						<BaseButton @click.prevent="dropdownSearchReplaceVisible = !dropdownSearchReplaceVisible">
							Find & Replace
						</BaseButton>
					</span>
					<span slot="dropdown-content" class="dropdown-content">
						<label for="searchTerm" class="dropdown-label">Search:</label>
						<input id="searchTerm" v-model="searchTerm" type="text" class="dropdown-input" />

						<label for="replaceTerm" class="dropdown-label">Replace:</label>
						<input id="replaceTerm" v-model="replaceTerm" type="text" class="dropdown-input" />

						<BaseButton @click.prevent="replaceAll" class="dropdown-button">Find/Replace All</BaseButton>

					</span>
				</BaseDropdown>
			</div>
		</div>

		<editor-content :editor="editor" class="editor-container__content" @focus="setFocus(true)" @blur="setFocus(false)"
			@contextmenu.prevent="openContextMenu($event, rowIndex, cellIndex)" />
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
			dropdownSearchReplaceVisible: false,
			dropdownAddVisible: false,
			dropdownRemoveVisible: false,
			dropdownToggleVisible: false,
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

		if (this.editable && this.editor.can().fixTables()) {
			this.editor.chain().focus().fixTables().run();
		}
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
		splitRow() {
			const { state, dispatch } = this.editor;
			const { selection } = state;
			const { $anchor, $head } = selection;
			const start = $anchor.start($anchor.depth - 1);
			const end = $head.start($head.depth - 1);
			const cells = [];
			state.doc.nodesBetween(start, end, (node, pos) => {
				if (node.type.name === "tableCell") {
					cells.push({ node, pos });
				}
			});
			const tr = state.tr;

			cells.forEach(({ node, pos }) => {
				const texts = node.textContent.split(/\s+/);
				texts.forEach((text, i) => {
					if (i > 0) {
						tr.insert(pos, state.schema.nodes.tableRow.create(null, [
							state.schema.nodes.tableCell.create(null, state.schema.text(text))
						]));
					} else {
						tr.setNodeMarkup(pos, null, null, state.schema.text(text));
					}
				});
			});
			dispatch(tr);
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
	errorCaptured(err, component, info) {
    this.error = err;
    console.error(`Error caught from ${component}: ${err}`);
    return false; // stops the error from propagating further
  },
}
</script>

<style lang="scss">
.editor-container {
  position: relative;
	flex-flow: column;
	width: 100%;

  &__content {
    // padding: 4rem 1rem;
		// min-width: 40vw;
		max-height: 60vh;
		overflow-x: scroll;
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
}

.menubar {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	padding: 5px 5px 0px 0px;
	color: white;
	text-decoration: none;

	.menubar__button {
		background-color: transparent;
		border: none;
		cursor: pointer;

		svg {
			fill: currentColor;
			height: 100%;
			width: 100%;
		}

		&:hover,
		&.is-active {
			background-color: $black-4;
		}

		&:disabled {
			cursor: not-allowed;
		}
	}

	.dropdown {
		position: relative;

		.button {
			cursor: pointer;
			&:hover,
			&--active {
				background: $black-4;
			}
		}
		.dropdown-content {
			.button {
				width: 100%;
			}
		}
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

  table {
    border-collapse: collapse;
    table-layout: auto;
    margin: 0;
    overflow: hidden;
		overflow-x: auto;
		@include overflow-scrollbar;

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

		tr {
			th {
				white-space: nowrap;
			}
		}

		td[colspan], th[colspan] {
			vertical-align: middle;
    }

    th {
			position: sticky;
    	top: 0;
    	z-index: 1;

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