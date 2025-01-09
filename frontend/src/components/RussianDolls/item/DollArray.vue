<template>
  <bk-form-item
    class="item-array"
    :label="item.title"
    :required="item.required"
    :property="item.property"
    :label-width="labelWidth"
    :desc="item.description">
    <div class="array-child-group" v-if="value?.length">
      <div class="array-child flex" v-for="(option, index) in value" :key="index">
        <DollIndex
          v-for="(child, idx) in children"
          :key="`${getRealProp(valueProp, index)}_${idx}`"
          :item="child"
          :item-index="value[idx]"
          :value="option"
          :value-prop="getRealProp(valueProp, index)"
          :label-width="110" />
        <i class="array-content-delete nodeman-icon nc-delete-2 ml10" @click.stop="() => deleteItem(index)" />
      </div>
      <div class="array-content-add" @click.stop="() => addItem(value.length - 1)">
        <i class="nodeman-icon nc-plus" />
        {{ item.title }}
      </div>
    </div>
    <div :class="['array-child-group', { 'is-error': isErr }]" v-else>
      <div class="array-content-add" @click.stop="() => addItem(-1)">
        <i class="nodeman-icon nc-plus" />
        {{ item.title }}
      </div>
      <div v-if="isErr" class="error-tip">{{ $t('必填项') }}</div>
    </div>
  </bk-form-item>
</template>

<script>
import { defineComponent, inject, ref, toRefs, onMounted } from 'vue';
import { formatSchema } from '../create';
import bus from '@/common/bus';

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
    labelWidth: {
      type: Number,
      default: 110,
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
    !props.value?.length && props.item.required && addItem(-1);
    const deleteItem = (index = 0) => {
      updateFormData?.({ ...props.item, property: getRealProp(props.valueProp, index) }, 'delete', index);
    };
    const isErr = ref(false);
    const validate = (cb) => {
      if (props.item.required && !props.value?.length) {
        isErr.value = true;
        cb(false);
      }else{
        isErr.value = false;
        cb(true);
      }
    }

    onMounted(() => {
      bus.$on('validate', validate)
    });

    return {
      ...toRefs(props),

      itemType,
      children,
      isErr,

      addItem,
      deleteItem,
      getRealProp,
      validate,
    };
  },
});

</script>
