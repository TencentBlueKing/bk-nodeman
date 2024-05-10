<template>
  <!-- <component is> -->
  <div class="item-object">
    <DollIndex
      v-for="child in item.children"
      :key="child.id"
      :item="child"
      :item-index="itemIndex"
      :value="value[child?.prop]"
      :value-prop="getRealProp(valueProp, child.prop)" />
  </div>
</template>

<script>
import { defineComponent, inject, toRefs } from 'vue';

export default defineComponent({
  props: {
    item: () => ({}),
    schema: () => ({}),
    itemIndex: -1,
    value: () => ({}),
    valueProp: '',
  },
  setup(props) {
    const getRealProp = inject('getRealProp');

    return {
      ...toRefs(props),

      getRealProp,
    };
  },
});

</script>

