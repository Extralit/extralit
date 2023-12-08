import { shallowMount } from "@vue/test-utils";
import RenderTableBaseComponent from "./RenderTable.base.component";
import { getColumnValidators } from "./validationUtils";
import { 
  columnSchemaToDesc, 
  incrementReferenceStr,
  getMaxStringValue,
} from "./tableUtils"; 


const options = {
  components: { RenderTableBaseComponent },
  propsData: {
    tableData: [], // data for table to display
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

  it("reacts to data changes", async () => {
    const wrapper = shallowMount(RenderTableBaseComponent, options);
    wrapper.setData({ tableData: [{ name: "John", age: 30 }] });
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.tabulator.getData()).toEqual([{ name: "John", age: 30 }]);
  });

  it("adds a new row when addRow is called", async () => {
    const wrapper = shallowMount(RenderTableBaseComponent, options);
    await wrapper.vm.$nextTick();
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