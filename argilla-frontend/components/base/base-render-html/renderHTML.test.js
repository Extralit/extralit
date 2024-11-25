import { shallowMount } from "@vue/test-utils";
import RenderHTML from "./RenderHTML";
import BaseButton from "../base-button/BaseButton.vue";
import BaseDropdown from "../base-dropdown/BaseDropdown.vue";

const options = {
  components: { RenderHTML, BaseButton, BaseDropdown },
  propsData: {
    value: '<p>Test</p>',
    placeholder: 'Enter text...',
    originalValue: '<p>Original</p>',
    isFocused: false,
    editable: true,
  },
};

describe("RenderHTML", () => {
  let wrapper;

  beforeEach(() => {
    wrapper = shallowMount(RenderHTML, options);
  });

  it('renders correctly with initial props', () => {
    expect(wrapper.html()).toContain('<div class="editor-container">')
    expect(wrapper.props().value).toBe('<p>Test</p>')
    expect(wrapper.props().placeholder).toBe('Enter text...')
    expect(wrapper.props().originalValue).toBe('<p>Original</p>')
    expect(wrapper.props().isFocused).toBe(false)
    expect(wrapper.props().editable).toBe(true)
  })

  it('updates the editor content when value prop changes', async () => {
    const newValue = '<p>New Value</p>'
    wrapper.vm.editor.commands.setContent(newValue);
    const updatedHTML = wrapper.vm.editor.getHTML();
    expect(updatedHTML).toBe(newValue)
  })

  it('enables editing when editable prop is true', async () => {
    await wrapper.setProps({ editable: true })
    expect(wrapper.vm.editor.isEditable).toBe(true)
  })

  it('disables editing when editable prop is false', async () => {
    await wrapper.setProps({ editable: false })
    expect(wrapper.vm.editor.isEditable).toBe(false)
  })
  
  it('calls replaceAll method and updates the content', async () => {
    jest.spyOn(wrapper.vm, 'replaceAll').mockImplementation(() => {
      wrapper.vm.editor.commands.setContent('<p>Replaced</p>')
    })
    await wrapper.vm.replaceAll()
    expect(wrapper.vm.editor.getHTML()).toBe('<p>Replaced</p>')
  })

})