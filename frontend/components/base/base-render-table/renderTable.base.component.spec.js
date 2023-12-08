import { shallowMount } from "@vue/test-utils";
import RenderTableBaseComponent from "./RenderTable.base.component";
import { getColumnValidators } from "./validationUtils";
import { 
  columnSchemaToDesc, 
  getTableDataFromRecords, 
  findMatchingRefValues,
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
});