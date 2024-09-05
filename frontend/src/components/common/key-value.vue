<template>
  <div class="bfArray">
    <template v-if="modelValue.length">
      <div v-for="(item, index) in modelValue" :key="index" class="key-value-item">
        <bk-input
          v-model="item.key"
          :placeholder="`Key ${index + 1}`"
          :class="['key-input', { 'is-error': schema.items.required?.includes('key') && item.key === '' && isValid[index]}]"
        >
          <span
            slot="append"
            class="error-tip is-error"
            v-bk-tooltips="$t('必填项')">
            <template v-if="schema.items.required?.includes('key') && item.key === '' && isValid[index]">
              <i class="bk-icon icon-exclamation-circle-shape"></i>
            </template>
          </span>
        </bk-input>
        <bk-input
          v-model="item.value"
          :placeholder="`Value ${index + 1}`"
          :class="['value-input', { 'is-error': schema.items.required?.includes('value') && item.value === '' && isValid[index] }]"
        >
          <span
            slot="append"
            class="error-tip is-error"
            v-bk-tooltips="$t('必填项')">
            <template v-if="schema.items.required?.includes('value') && item.value === '' && isValid[index]">
              <i class="bk-icon icon-exclamation-circle-shape"></i>
            </template>
          </span>
        </bk-input>
        <!-- 新增的增加按钮 -->
        <bk-button @click="addItemAt(index)" icon="bk-icon icon-plus-circle" class="add-btn"></bk-button>
        <bk-button @click="removeItem(index)" icon="bk-icon icon-minus-circle" class="remove-btn"></bk-button>
      </div>
    </template>
    <div v-else>
      <div :class="{'add-bar': schema['ui:props'].size === 'large'}" @click.stop="() => addItem()">
        <i class="nodeman-icon nc-plus" />
        {{ $t('添加') }}{{ schema['ui:props'].size === 'large' ? schema.title : '' }}
      </div>
    </div>
    
  </div>
</template>

<script>
import { defineComponent, ref, watch, onMounted } from 'vue';
import bus from '@/common/bus';

export default defineComponent({
  name: 'KeyValueComponent',
  props: {
    schema: {
      type: Object,
      default: () => ({}),
    },
    // 当前路径（唯一标识）
    path: {
      type: String,
      default: '',
    },
    // 是否必须字段
    required: {
      type: Boolean,
      default: false,
    },
    // 全量数据（只读）
    rootData: {
      type: Object,
      default: () => ({}),
    },
    // 当前值
    value: {
      type: [String, Number, Array, Object, Boolean],
    },
    // 布局配置
    layout: {
      type: Object,
      default: () => ({}),
    },
    // 当前全局变量上下文
    context: {
      type: Object,
      default: () => ({}),
    },
    // 当前项是否可移除
    removeable: {
      type: Boolean,
      default: false,
    },
  },
  setup(props, { emit }) {
    const modelValue = ref([...props.value]);
    // 填充校验，true表示已校验
    const isValid = ref(new Array(props.value.length).fill(false));

    watch(modelValue, (newValue) => {
      emit('input', newValue);
    }, { deep: true });

    const addItem = () => {
      isValid.value.push(false);
      modelValue.value.push({ key: '', value: '' });
    };

    // 在指定位置插入新项
    const addItemAt = (index) => {
      isValid.value.push(false);
      modelValue.value.splice(index + 1, 0, { key: '', value: '' });
    };

    const removeItem = (index) => {
      isValid.value.pop();
      modelValue.value.splice(index, 1);
    };
    const handleBlur = (index) => {
      isValid.value[index] = true;
    }
    const handleFocus = (index) => {
      isValid.value[index] = false;
    }
    const validate = (cb) => {
      isValid.value.fill(true);
      isValid.value = [...isValid.value];
      const hasEmpty = modelValue.value.some((item) => 
        (item.key === '' && props.schema.items.required?.includes('key'))
        || (item.value === '' && props.schema.items.required?.includes('value')));
      if (hasEmpty) {
        cb(false);
      }else{
        cb(true);
      }
    }
    onMounted(() => {
      bus.$on('validate', validate)
    });
    return {
      isValid,
      modelValue,
      handleBlur,
      handleFocus,
      addItem,
      addItemAt,
      removeItem
    };
  }
});
</script>

<style lang="postcss" scoped>
.key-value-item {
  display: flex;
  align-items: center;
  flex: 1;
  padding-right: 20px;
  background: #f5f7fa;
  margin-bottom: 12px;
  width: 100%;
}

.key-input{
  margin-right: 20px;
}

.add-btn,.remove-btn {
  border: none;
  background-color: transparent;
}

.add-bar {
  border: 1px dashed #3a84ff;
  border-radius: 2px;
  color: #3a84ff;
  cursor: pointer;
  text-align: center;
}

.key-input, .value-input {
  position: relative;
}
.is-error {
  /deep/ input[type=text] {
    border-color: #ff5656;
    color: #ff5656;
  }
  &.error-tip {
    position: absolute;
    right: 8px;
    font-size: 16px;
    color: #ea3636;
    cursor: pointer;
  }
}
/deep/ .bk-form-control .group-box {
  border: none !important;
}
</style>