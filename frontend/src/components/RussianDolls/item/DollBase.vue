<template>
  <bk-form-item
    :label="item.title"
    :required="item.required"
    :property="valueProp"
    :desc="item.description"
    :rules="item.rules">
    <component
      :is="item.component"
      v-bind="item.props"
      :value="value"
      @focus="inputFocus"
      @blur="inputBlur"
      @change="baseValueChange"
    />
  </bk-form-item>
</template>

<script>
import { defineComponent, inject, toRefs } from 'vue';

export default defineComponent({
  props: {
    item: {
      type: Object,
      default: () => ({}),
    },
    schema: {
      type: Object,
      default: () => ({}),
    },
    itemIndex: {
      type: Number,
      default: -1,
    },
    value: {
      type: String,
      default: '',
    },
    valueProp: {
      type: String,
      default: '',
    },
  },
  setup(props) {
    const updateFormData = inject('updateFormData');
    const inputFocus = inject('inputFocus');
    const inputBlur = inject('inputBlur');

    const baseValueChange = (val) => {
      const value = val.trim();
      const isNumber = props.schema.type === 'number';
      let formatValue = isNumber ? parseFloat(value) || 0 : value;

      // 调过bia 以单引号开头、结尾的值直接用作字符串
      if (!isNumber || !/^'.*'$/.test(value)) {
        try {
          formatValue = JSON.parse(value);
        } catch (err) {}
      }
      updateFormData?.({ ...props.item, property: props.valueProp }, 'assign', formatValue);
    };

    return {
      ...toRefs(props),

      baseValueChange,
      inputFocus,
      inputBlur,
    };
  },
});
</script>
