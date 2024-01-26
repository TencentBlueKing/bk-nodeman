<template>
  <bk-form
    class="russian-dolls-form"
    ref="russianDollsFormRef"
    :model="formModel"
    :rules="rules"
    :label-width="labelWidth">
    <DollIndex :value-prop="''" :value="formModel" :item="baseForm" :item-index="0" />
  </bk-form>
</template>

<script>
import { defineComponent, provide, ref, toRefs, watch } from 'vue';
import { getRealProp, initSchema } from './create';
import { deepClone } from '@/common/util';

export default defineComponent({
  name: 'RussianDollsForm',
  props: {
    data: {
      type: Array,
      default: () => [],
    },
    layout: {
      type: Array,
      default: () => [],
    },
    rules: {
      type: Object,
      default: () => ({}),
    },
    value: {
      type: Object,
      default: () => ({}),
    },
    labelWidth: {
      type: Number,
      default: 150,
    },
  },
  emits: ['change', 'focus', 'blur'],
  setup(props, { emit }) {
    const russianDollsFormRef = ref();
    const baseForm = ref({});
    const formatList = ref([]);
    const formModel = ref(deepClone(props.value));

    const typeArr = ['object', 'array'];

    const getLastLevelData = (propItem) => {
      const { property, type } = propItem;
      const keys = property.split('.');
      // 通过类型 来确定取值是倒数第一层或第二层
      const lastIndex = type === 'object' ? keys.length : keys.length - 1;
      let lastLevelData = formModel.value;
      keys.forEach((key, index) => {
        if (lastIndex > index) {
          lastLevelData = lastLevelData[key];
        }
      });
      return lastLevelData;
    };

    // type: add delete assign
    // target: index or value
    const updateFormData = (propItem, type, target) => {
      const data = getLastLevelData(propItem);
      const { property } = propItem;
      let prop = '';
      let value = target;
      if (type === 'assign') {
        if (Array.isArray(data)) {
          const propKey = property?.split('.') || [];
          prop = propKey[propKey.length - 1] || 0;
          data[prop] = target;
        } else {
          prop = propItem.prop;
          data[propItem.prop] = target;
        }
      } else {
        if (type === 'add') {
          const [child] = getDefaultValue(propItem);
          data.splice(target, 0, child);
        } else {
          data.splice(target, 1);
        }
        value = data;
      }
      emit('change', { property, prop, value });
    };

    const getDefaultValue = (propItem, isInit) => {
      if (typeArr.includes(propItem.type)) {
        if (propItem.type === 'object') {
          return propItem.children.reduce((obj, child) => {
            obj[child.prop] = getDefaultValue(child, isInit);
            return obj;
          }, {});
        }
        return isInit ? [] : [getDefaultValue(propItem.children[0], true)];
      }
      return propItem.defaultValue;
    };

    const isDifferentType = (itemConfig, form) => {
      const { type, prop } = itemConfig;
      let different = false;
      if (['array', 'object'].includes(type) && typeof form !== 'object') {
        different = true;
      }
      different =  type === 'array'
        ? !Array.isArray(form[prop])
        : (typeof form[prop]) !== type;

      return different;
    };

    // 格式化form-item 属性的相关配置
    const initFormList = (data) => {
      const schema = initSchema(data);
      baseForm.value = schema;
      formatList.value.splice(0, formatList.value.length, ...schema.children);
    };
    // 补齐form需要的数据
    const completionArrayData = (list, form) => {
      // 很关键。form一定要保证是个obj
      const formData = typeof form === 'object' && !Array.isArray(form)
        ? deepClone(form)
        : {};
      try {
        list.forEach((item) => {
          if (isDifferentType(item, formData) || !Object.prototype.hasOwnProperty.call(formData, item.prop)) {
            formData[item.prop] = getDefaultValue(item, true);
          } else {
            if (item.type === 'array') {
              formData[item.prop] = formData[item.prop]
                .map(formItem => completionArrayData(item.children[0].children, formItem));
            }
          }
        });
        return formData;
      } catch (err) {
        console.log(err);
        return {};
      }
    };

    const validate = () => russianDollsFormRef.value?.validate();
    const clearValidate = () => russianDollsFormRef.value?.clearError();
    const getFormData = () => deepClone(formModel.value);
    const inputFocus = (value, event) => {
      emit('focus', value, event);
    };
    const inputBlur = (value, event) => {
      emit('blur', value, event);
    };

    initFormList(props.data);
    formModel.value = completionArrayData(formatList.value, props.value);

    provide('updateFormData', updateFormData);
    provide('inputFocus', inputFocus);
    provide('inputBlur', inputBlur);
    provide('getRealProp', getRealProp);

    watch(() => props.data, (value) => {
      initFormList(value);
    }, { deep: true });

    // 需要补齐数组的数据
    watch(() => props.value, () => {
      formModel.value = completionArrayData(formatList.value, props.value);
    }, { deep: true });

    return {
      ...toRefs(props),
      russianDollsFormRef,

      formModel,
      baseForm,
      formatList,
      validate,
      clearValidate,
      getFormData,
    };
  },
});

</script>

<style lang="postcss">
@import "./DollForm.css";
</style>
