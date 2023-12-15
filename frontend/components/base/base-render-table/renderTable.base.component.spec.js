import { shallowMount, createLocalVue } from "@vue/test-utils";
import RenderTableBaseComponent from "./RenderTable.base.component";
import {
  TabulatorFull as Tabulator,
} from "tabulator-tables";
import Vuex from "vuex";
// import { getColumnValidators } from "./validationUtils";
// import { 
//   columnSchemaToDesc, 
//   incrementReferenceStr,
//   getMaxStringValue,
// } from "./tableUtils"; 

const localVue = createLocalVue();
localVue.use(Vuex);

let store = null;
const getters = {};
store = new Vuex.Store({ getters });

let wrapper = null;

const options = {
  components: { RenderTableBaseComponent },
  propsData: {
    tableData: '{"schema": {"fields": [{"name": "study_ref", "type": "string"}, {"name": "itncondition_ref", "type": "string"}, {"name": "reference", "type": "string"}, {"name": "Anoph_spp", "type": "string"}, {"name": "Source", "type": "string"}, {"name": "Total_mosquitoes", "type": "string"}], "primaryKey": ["study_ref", "itncondition_ref", "reference"], "pandas_version": "1.4.0"}, "data": [{"study_ref": "Winkler2012-01S", "itncondition_ref": "Winkler2012-01N", "reference": "Winkler2012-01S-01N-01E", "Anoph_spp": "gambiae s.s.", "Source": "Lab", "Total_mosquitoes": "50"}, {"study_ref": "Winkler2012-01S", "itncondition_ref": "Winkler2012-02N", "reference": "Winkler2012-01S-02N-01E", "Anoph_spp": "gambiae s.s.", "Source": "Lab", "Total_mosquitoes": "50"}, {"study_ref": "Winkler2012-01S", "itncondition_ref": "Winkler2012-04N", "reference": "Winkler2012-01S-04N-01E", "Anoph_spp": "gambiae s.s.", "Source": "Lab", "Total_mosquitoes": "50"}, {"study_ref": "Winkler2012-01S", "itncondition_ref": "Winkler2012-05N", "reference": "Winkler2012-01S-05N-01E", "Anoph_spp": "gambiae s.s.", "Source": "Lab", "Total_mosquitoes": "50"}, {"study_ref": "Winkler2012-02S", "itncondition_ref": "Winkler2012-01N", "reference": "Winkler2012-02S-01N-01E", "Anoph_spp": "funestus", "Source": "Wild", "Total_mosquitoes": "140"}], "validation": {"schema_type": "dataframe", "version": "0.18.0", "columns": {"Anoph_spp": {"title": null, "description": "Anopheles species studied - enter each species as a separate row", "dtype": "str", "nullable": true, "checks": null, "unique": false, "coerce": false, "required": true, "regex": false}, "Source": {"title": null, "description": "Were the mosquitoes sourced from the wild or are they a lab strain? Enter \'Wild\' or \'Lab\'", "dtype": "str", "nullable": true, "checks": {"isin": ["Wild", "Lab"]}, "unique": false, "coerce": false, "required": true, "regex": false}, "Total_mosquitoes": {"title": null, "description": "Starting number of mosquitoes", "dtype": "int64", "nullable": true, "checks": {"greater_than_or_equal_to": 0}, "unique": false, "coerce": false, "required": true, "regex": false}}, "checks": null, "index": [{"title": null, "description": null, "dtype": "str", "nullable": false, "checks": null, "name": "reference", "unique": true, "coerce": false}, {"title": null, "description": null, "dtype": "str", "nullable": false, "checks": null, "name": "study_ref", "unique": false, "coerce": false}, {"title": null, "description": null, "dtype": "str", "nullable": false, "checks": null, "name": "itncondition_ref", "unique": false, "coerce": false}], "dtype": null, "coerce": true, "strict": true, "name": "EntomologicalOutcome", "ordered": false, "unique": null, "report_duplicates": "all", "unique_column_names": false, "add_missing_columns": false, "title": null, "description": null}}',
    // tableData: '',
    editable: false, // whether the table is editable
  },
  localVue,
  store,
  mocks: {
    $nuxt: {
      $on: jest.fn(),
      // mock other methods as needed
    },
  },
};

describe("RenderTableBaseComponent", () => {
  it("renders a table", () => {
    const wrapper = shallowMount(RenderTableBaseComponent, options);
    expect(wrapper.find('div').exists()).toBe(true);
  });

  it("initializes Tabulator on mount", () => {
    const wrapper = shallowMount(RenderTableBaseComponent, options);
    expect(wrapper.vm.tabulator).not.toBe(null);
  });

  it("adds a new row when addRow is called", async () => {
    const wrapper = shallowMount(RenderTableBaseComponent, options);
    await wrapper.vm.$nextTick();
    console.log(wrapper.vm.table);
    const initialRowCount = wrapper.vm.table.getData().length;
    wrapper.vm.addRow();
    expect(wrapper.vm.table.getData().length).toBe(initialRowCount + 1);
  });

  it("adds a new column when addColumn is called", async () => {
    const wrapper = shallowMount(RenderTableBaseComponent, options);
    await wrapper.vm.$nextTick();
    const initialColumnCount = wrapper.vm.table.getColumns().length;
    wrapper.vm.addColumn();
    expect(wrapper.vm.table.getColumns().length).toBe(initialColumnCount + 1);
  });

  it("deletes a selected row when deleteRow is called", async () => {
    const wrapper = shallowMount(RenderTableBaseComponent, options);
    await wrapper.vm.$nextTick();
    wrapper.vm.table.selectRow(1); // Assuming the table has at least one row
    const initialRowCount = wrapper.vm.table.getData().length;
    wrapper.vm.dropRow();
    expect(wrapper.vm.table.getData().length).toBe(initialRowCount - 1);
  });
});