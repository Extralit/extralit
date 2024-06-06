import { shallowMount } from "@vue/test-utils";
import RenderTable from "./RenderTable.base.component";

const options = {
  components: { RenderTable },
  propsData: {
    tableData: '',
    editable: true,
  },
};

describe('RenderTable', () => {
  let wrapper

  beforeEach(() => {
    wrapper = shallowMount(RenderTable, options)
  })

  it('renders correctly with initial props', () => {
    expect(wrapper.html()).toContain('<div class="table-container">')
    expect(wrapper.props().tableData).toBe('')
    expect(wrapper.props().editable).toBe(true)
  })

});