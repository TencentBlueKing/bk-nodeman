<template>
  <div class="item-key-value bk-form-item">
    <template v-if="value?.length">
      <bk-form-item
        v-for="(child, idx) in value"
        :required="item.required"
        :label-width="labelWidth"
        :label="idx ? '' : item.title"
        :key="idx">
        <div class="flex">
          <div class="flex1" style="flex: 1">
            <bk-input
              :class="{'is-error': children[0].required && child[children[0].prop] === '' && isValid[idx]}"
              :value="child[children[0].prop]"
              :placeholder="children[0].title"
              @focus="inputFocus"
              @change="(val) => updateKeyValue(val, idx, children[0])"/>
            <span
              v-if="children[0].required && child[children[0].prop] === '' && isValid[idx]"
              class="error-tip is-error"
              v-bk-tooltips="$t('必填项')">
              <i class="bk-icon icon-exclamation-circle-shape"></i>
            </span>
          </div>
          <div class="pl10 pr10">=</div>
          <div class="flex1" style="flex: 1">
            <bk-input
              :class="{'is-error': children[1].required && child[children[1].prop] === '' && isValid[idx]}"
              :value="child[children[1].prop]"
              :placeholder="children[1].title"
              @blur="inputBlur"
              @change="(val) => updateKeyValue(val, idx, children[1])" />
            <span
              v-if="children[1].required && child[children[1].prop] === '' && isValid[idx]"
              class="error-tip is-error"
              v-bk-tooltips="$t('必填项')">
              <i class="bk-icon icon-exclamation-circle-shape"></i>
            </span>
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
    <bk-form-item v-else :label="item.title" :label-width="labelWidth">
      <div class="array-content-add" @click.stop="() => addItem(-1)">
        <i class="nodeman-icon nc-plus" />
        {{ item.title }}
      </div>
    </bk-form-item>
  </div>
</template>

<script>
import { computed, defineComponent, inject, ref, toRefs, onMounted } from 'vue';
import { formatSchema } from '../create';
import bus from '@/common/bus';

export default defineComponent({
  props: {
    item: () => ({}),
    schema: () => ({}),
    itemIndex: -1,
    value: () => [],
    valueProp: '',
    labelWidth: {
      type: Number,
      default: 110,
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
    const isValid = ref([]);
    const addItem = (index) => {
      isValid.value.push(false);
      const realIndex = index + 1;
      updateFormData?.({ ...props.item, property: getRealProp(props.valueProp, realIndex) }, 'add', index + 1);
    };
    const deleteItem = (index) => {
      isValid.value.pop();
      updateFormData?.({ ...props.item, property: getRealProp(props.valueProp, index) }, 'delete', index);
    };
    const validate = (cb) => {
      isValid.value.fill(true);
      isValid.value = [...isValid.value];
      const hasEmpty = props.value.some((item) => item[children.value[0].prop] === '' || item[children.value[1].prop] === '');
      if (hasEmpty) {
        cb(false);
      }else{
        cb(true);
      }
    }
    onMounted(() => {
      bus.$on('validateKV', validate)
    });

    return {
      ...toRefs(props),

      keyModel,
      valueModel,
      children,
      disabledMinus,
      isValid,

      updateKeyValue,
      addItem,
      deleteItem,
      inputFocus,
      inputBlur,
    };
  },
});
</script>
