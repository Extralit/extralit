export default {
  // Dual-purpose binding (Vue 3): legacy `:value`/`@input` consumers keep working, and
  // `v-model` consumers bind through `modelValue`/`update:modelValue`. Without the
  // `update:modelValue` emit, every `<BaseInput v-model="x">` silently fails to update
  // (Vue 2's `model:` option that used to wire `value`/`input` was removed).
  emits: ["change", "input", "update:modelValue", "focus", "blur"],
  props: {
    value: [String, Number],
    modelValue: [String, Number],
    debounce: {
      type: Number,
      default: 1e2,
    },
    disabled: Boolean,
    required: Boolean,
    maxlength: [Number, String],
    name: String,
    placeholder: String,
    readonly: Boolean,
  },
  data() {
    return {
      timeout: 0,
    };
  },
  watch: {
    value() {
      this.updateValues();
    },
    modelValue() {
      this.updateValues();
    },
    disabled() {
      this.setParentDisabled();
    },
    required() {
      this.setParentRequired();
    },
    placeholder() {
      this.setParentPlaceholder();
    },
    maxlength() {
      this.handleMaxLength();
    },
  },
  methods: {
    handleMaxLength() {
      this.parentContainer.enableCounter = this.maxlength > 0;
      this.parentContainer.counterLength = this.maxlength;
    },
    lazyEventEmitter() {
      if (this.timeout) {
        window.clearTimeout(this.timeout);
      }
      this.timeout = window.setTimeout(() => {
        this.$emit("change", this.$el.value);
        this.$emit("input", this.$el.value);
        this.$emit("update:modelValue", this.$el.value);
      }, this.debounce);
    },
    setParentValue(value) {
      this.parentContainer.setValue(value || this.$el.value);
    },
    setParentDisabled() {
      this.parentContainer.isDisabled = this.disabled;
    },
    setParentRequired() {
      this.parentContainer.isRequired = this.required;
    },
    setParentPlaceholder() {
      this.parentContainer.hasPlaceholder = !!this.placeholder;
    },
    updateValues() {
      this.$nextTick(() => {
        const newValue = this.$el.value || this.modelValue || this.value;

        this.setParentValue(newValue);
        this.parentContainer.inputLength = newValue ? newValue.length : 0;
      });
    },
    onFocus(event) {
      if (this.parentContainer) {
        this.parentContainer.isFocused = true;
      }

      this.$emit("focus", this.$el.value, event);
    },
    onBlur(event) {
      this.parentContainer.isFocused = false;
      this.setParentValue();

      this.$emit("blur", this.$el.value, event);
    },
    onInput() {
      this.updateValues();
      this.lazyEventEmitter();
    },
  },
};
