<template>
	<div ref="table" class="table-container"></div>
</template>

<script>
import { TabulatorFull as Tabulator } from 'tabulator-tables';
import "tabulator-tables/dist/css/tabulator.min.css";

export default {
	name: 'RenderTableBaseComponent',
	props: {
		tableData: {
			type: String,
			required: true,
		},
		editable: {
			type: Boolean,
			default: false,
		},
	},
	data() {
		return {
			tabulator: null,
		};
	},
	computed: {
		tableJSON: {
			get() {
				try {
					return JSON.parse(this.tableData);
				} catch (error) {
					console.error("Failed to parse JSON:", error);
					return null;
				}
			},
			set(json) {
				this.$nuxt.$emit('on-update-response-tabledata', JSON.stringify(json));
			}
		},
		editableConfig() {
			if (this.editable) {
				return {
					editor: "textarea",
					editorParams: {
						selectContents: true,
					},
					cellEdited: (cell) => {
						this.tableJSON = this.tabulator.getData();
					}
				};
			}
			return {};
		},
		columns() {
			if (!this.tableJSON || !this.tableJSON.length) return [];
			let columns = Object.keys(this.tableJSON[0]).map((key, index) => ({
				title: key,
				field: key,
				headerSort: false,
				frozen: index === 0 ? true : false,
				...this.editableConfig, // Spread the editableConfig here
			}));
			// columns.unshift({ rowHandle: true, formatter: "handle", headerSort: false, frozen: true, width: 30, minWidth: 30 },);
			
			return columns
		},
	},
	mounted() {
		this.tabulator = new Tabulator(this.$refs.table, {
			data: this.tableJSON,
			tabEndNewRow: true,
			reactiveData: true,
			// clipboard: true,
			// clipboardPasteAction: "replace",
			// autoColumns: true,
			columns: this.columns,
			resizableColumnFit: true,
			layout: "fitDataTable",
		});
	},
};
</script>

<style scoped lang="scss">
.table-container {
	max-width: 645px;
  overflow-x: auto;
  position: relative;
}
</style>