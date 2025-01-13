<template>
  <DollKeyValue
    v-if="item.component === 'bfArray'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp"
    :label-width="labelWidth" />
  <DollObject
    v-else-if="item.type === 'object'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp"
    :label-width="labelWidth" />
  <DollArray
    v-else-if="item.type === 'array'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp"
    :label-width="labelWidth" />
  <DollBase
    v-else
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp"
    :label-width="labelWidth" />
</template>

<script>
import { defineComponent, toRefs } from 'vue';

export default defineComponent({
  props: {
    item: {
      type: Object,
      default: () => ({}),
    },
    itemIndex: {
      type: Number,
      default: -1,
    },
    value: {
      type: Object,
      default: () => ({}),
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
    return {
      ...toRefs(props),
    };
  },
});

</script>
