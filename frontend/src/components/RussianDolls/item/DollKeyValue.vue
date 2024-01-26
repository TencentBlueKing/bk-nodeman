<template>
  <div class="item-key-value bk-form-item">
    <template v-if="value?.length">
      <bk-form-item
        v-for="(child, idx) in value"
        :label="idx ? '' : item.title"
        :key="idx">
        <div class="flex">
          <div class="flex1" style="flex: 1">
            <bk-input
              :value="child[children[0].prop]"
              :placeholder="children[0].title"
              @focus="inputFocus"
              @change="(val) => updateKeyValue(val, idx, children[0])" />
          </div>
          <div class="pl10 pr10">=</div>
          <div class="flex1" style="flex: 1">
            <bk-input
              :value="child[children[1].prop]"
              :placeholder="children[1].title"
              @blur="inputBlur"
              @change="(val) => updateKeyValue(val, idx, children[1])" />
          </div>
          <div class="child-btns ml10">
            <i
              class="nodeman-icon nc-plus"
              @click.stop="() => addItem(idx)" />
            <!-- :class="['nodeman-icon nc-minus ', { 'disabled': disabledMinus }]" -->
            <i
              class="nodeman-icon nc-minus"
              @click.stop="() => deleteItem(idx)" />
          </div>
        </div>
      </bk-form-item>
    </template>
    <bk-form-item v-else :label="item.title">
      <div class="array-content-add" @click.stop="() => addItem(-1)">
        <i class="nodeman-icon nc-plus" />
        {{ item.title }}
      </div>
    </bk-form-item>
  </div>
</template>

<script>
import { computed, defineComponent, inject, ref, toRefs } from 'vue';
import { formatSchema } from '../create';

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
      type: Array,
      default: () => [],
    },
    valueProp: {
      type: String,
      default: '',
    },
  },
  emits: ['add', 'delete'],
  setup(props) {
    const updateFormData = inject('updateFormData');
    const getRealProp = inject('getRealProp');
    const inputFocus = inject('inputFocus');
    const inputBlur = inject('inputBlur');

    const keyModel = ref('');
    const valueModel = ref('');
    const children = ref(formatSchema(props.schema.items, props.item.property, props.item.level + 1).children || []);

    const disabledMinus = computed(() => props.value.length < 2);

    const updateKeyValue = (value, index, item) => {
      updateFormData?.({
        ...item,
        property: getRealProp(props.valueProp, `${index}.${item.prop}`),
      }, 'assign', value);
    };
    const addItem = (index) => {
      const realIndex = index + 1;
      updateFormData?.({ ...props.item, property: getRealProp(props.valueProp, realIndex) }, 'add', index + 1);
    };
    const deleteItem = (index) => {
      updateFormData?.({ ...props.item, property: getRealProp(props.valueProp, index) }, 'delete', index);
    };

    return {
      ...toRefs(props),

      keyModel,
      valueModel,
      children,
      disabledMinus,

      updateKeyValue,
      addItem,
      deleteItem,
      inputFocus,
      inputBlur,
    };
  },
});
</script>
