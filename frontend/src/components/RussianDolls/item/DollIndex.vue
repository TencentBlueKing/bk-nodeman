<template>
  <DollKeyValue
    v-if="item.component === 'bfArray'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp" />
  <DollObject
    v-else-if="item.type === 'object'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp" />
  <DollArray
    v-else-if="item.type === 'array'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp" />
  <DollBase
    v-else
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex"
    :value="value"
    :value-prop="valueProp" />
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
  },
  setup(props) {
    return {
      ...toRefs(props),
    };
  },
});

</script>
