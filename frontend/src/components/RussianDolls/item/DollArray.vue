<template>
  <bk-form-item
    class="item-array"
    :label="item.title"
    :required="item.required"
    :property="item.property"
    :desc="item.description">
    <div class="array-child-group" v-if="value?.length">
      <div class="array-child flex" v-for="(option, index) in value" :key="option">
        <DollIndex
          v-for="(child, idx) in children"
          :key="`${option}_${idx}`"
          :item="child"
          :item-index="value[idx]"
          :value="option"
          :value-prop="getRealProp(valueProp, index)" />
        <i class="array-content-delete nodeman-icon nc-delete-2 ml10" @click.stop="() => deleteItem(index)" />
      </div>
      <div class="array-content-add" @click.stop="() => addItem(value.length - 1)">
        <i class="nodeman-icon nc-plus" />
        {{ item.title }}
      </div>
    </div>
    <div v-else class="array-content-add" @click.stop="() => addItem(-1)">
      <i class="nodeman-icon nc-plus" />
      {{ item.title }}
    </div>
  </bk-form-item>
</template>

<script>
import { defineComponent, inject, ref, toRefs } from 'vue';
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
    value: {
      type: Array,
      default: () => [],
    },
    valueProp: {
      type: String,
      default: '',
    },
  },
  setup(props) {
    const updateFormData = inject('updateFormData');
    const getRealProp = inject('getRealProp');

    const itemType = ref(props.item.children?.[0]?.type || 'string');

    const children = ref([formatSchema(props.schema.items, props.item.property, props.item.level + 1)]);

    const addItem = (index = 0) => {
      const realIndex = index + 1;
      updateFormData?.({ ...props.item, property: getRealProp(props.valueProp, realIndex) }, 'add', index + 1);
    };
    const deleteItem = (index = 0) => {
      updateFormData?.({ ...props.item, property: getRealProp(props.valueProp, index) }, 'delete', index);
    };

    return {
      ...toRefs(props),

      itemType,
      children,

      addItem,
      deleteItem,
      getRealProp,
    };
  },
});

</script>
