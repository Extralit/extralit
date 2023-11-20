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
	},
	data() {
		return {
			tabulator: null,
		};
	},
	computed: {
		tableJSON: {
			get() {
				if (!this.tableData) return [];
				try {
					return JSON.parse(this.tableData);
				} catch (error) {
					console.error("Failed to parse JSON:", error);
					return null;
				}
			},
			set(newValue) {
				console.log('set', JSON.stringify(newValue))
				this.$emit('update:tableData', JSON.stringify(newValue));
			}
		},
		columns() {
			if (!this.tableJSON || !this.tableJSON.length) return [];
			return Object.keys(this.tableJSON[0]).map((key) => ({
				title: key,
				field: key,
				editor: "input",
			}));
		},
	},
	mounted() {
		this.tabulator = new Tabulator(this.$refs.table, {
			data: this.tableJSON,
			reactiveData: true,
			columns: this.columns,
			// cellEdited: () => {
			// 	console.log('cellEdited', this.tabulator.getData())
			// 	this.tableJSON = this.tabulator.getData();
			// }
		});
	},
};
</script>

<style scoped lang="scss">
.table-container {
	max-width: 645px;
  overflow-x: auto;
}
</style>