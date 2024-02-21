<template>
  <div class="setup-header batch-able">
    <div ref="tipSpanRef" class="'header-label">
      <span :title="label">{{ label }}</span>
    </div>
    <bk-popover
      v-if="batch"
      class="batch-btn"
      ref="batchRef"
      theme="light batch-edit pkg-batch"
      trigger="manual"
      placement="bottom"
      :tippy-options="{ 'hideOnClick': false }"
      :on-show="handleOnShow"
      :on-hide="handleOnHide">
      <span
        :class="['batch-icon nodeman-icon nc-bulk-edit', { 'active': isActive }]"
        v-bk-tooltips.top="{
          'content': $t('批量编辑', { title: '' }),
          'delay': [300, 0]
        }"
        @click="handleBatchClick">
      </span>
      <template #content>
        <div class="batch-edit">
          <div class="batch-edit-title pb0">{{ $t('批量编辑', { title: label }) }}</div>
          <div class="batch-edit-sub-title">{{ $t('统一填充') }}</div>
          <div class="batch-edit-content" v-if="isShow">
            <bk-tag-input
              allow-create
              searchable
              has-delete-icon
              use-group
              trigger="focus"
              :list="options"
              :placeholder="$t('请输入或选择')"
              :tag-tpl="tagTpl"
              v-model="value" />
          </div>
          <div class="footer">
            <bk-button theme="primary" size="small" @click="handleBatchConfirm">{{ $t('确定') }}</bk-button>
            <bk-button size="small" @click="handleBatchCancel">{{ $t('取消') }}</bk-button>
          </div>
        </div>
      </template>
    </bk-popover>
  </div>
</template>
<script lang="ts">
import { IPkgTagOpt } from '@/types/agent/pkg-manage';
import { ref, defineComponent, reactive, getCurrentInstance, toRefs, PropType } from 'vue';

export default defineComponent({
  name: 'PkgThead',
  props: {
    moduleValue: {
      type: Array as PropType<string[]>,
      default: [],
    },
    label: {
      type: String,
      default: '',
    }, // 表头label
    batch: {
      type: Boolean,
      default: false,
    }, // 是否有批量编辑框
    isBatchIconShow: {
      type: Boolean,
      default: true,
    }, // 是否显示批量编辑图标
    options: {
      type: Array,
      default: () => ([]),
    }, // 下拉框数据源
    placeholder: {
      type: String,
      default: '',
    },
  },
  emits: ['confirm'],
  setup(props, { emit }) {
    const proxy = getCurrentInstance()?.proxy;

    const batchRef = ref<any>();
    const tipSpanRef = ref<any>();
    const tipRef = ref<any>();

    const state = reactive<{
      isActive: boolean;
      value: string[];
      isShow: boolean;
    }>({
      isActive: false, // 当前批量编辑icon是否激活
      value: [],
      isShow: false,
    });

    const handleBatchClick = () => {
      if (state.isActive) {
        handleBatchCancel();
      } else {
        batchRef.value?.instance.show();
        state.isActive = true;
      }
    };
    const handleBatchConfirm = () => {
      handleBatchCancel();
      emit('confirm',  { value: state.value });
    };
    const handleBatch = (value: any) => {
      state.value = value;
      handleBatchConfirm();
    };
    const handleBatchCancel = () => {
      state.isActive = false;
      batchRef.value?.instance.hide();
    };
    const handleOnShow = () => {
      state.value.splice(0, state.value.length, ...props.moduleValue);
      state.isShow = true;
    };
    const handleOnHide = () => {
      state.isShow = false;
    };
    const hidePopover = (instance: any) => {
      if (instance === proxy) return;
      handleBatchCancel();
    };

    const tagTpl = (opt: IPkgTagOpt) => proxy?.$createElement('div', {
      class: `tag ${opt.className}`,
    }, [
        proxy?.$createElement('span', { class: 'text' }, opt.name),
    ]);

    return {
      ...toRefs(props),
      ...toRefs(state),

      batchRef,
      tipSpanRef,
      tipRef,

      handleBatchClick,
      handleBatchConfirm,
      handleBatch,
      handleBatchCancel,
      handleOnShow,
      handleOnHide,
      hidePopover,
      tagTpl,
    };
  },
});
</script>
<style lang="postcss">
  @import "@/css/variable.css";

  .setup-header {
    display: inline-flex;
    align-items: center;
    font-weight: normal;
    text-align: left;
    width: 100%;
    overflow: hidden;
    &.is-center {
      justify-content: center;
    }
    .header-label {
      position: relative;
      display: inline-block;
      line-height: 16px;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
      &-required {
        padding-right: 6px;
        &::after {
          content: "*";
          color: #ff5656;
          position: absolute;
          top: 2px;
          right: 0;
        }
      }
      &-tips {
        border-bottom: 1px dashed #c4c6cc;
        cursor: default;
      }
    }
    .batch-btn {
      flex-shrink: 0;
    }
    .batch-icon {
      margin-left: 6px;
      font-size: 16px;
      color: #979ba5;
      cursor: pointer;
      outline: 0;
      &:hover {
        color: #3a84ff;
      }
      &.active {
        color: #3a84ff;
      }
    }
  }

  .pkg-batch-theme {
    .batch-edit {
      padding-top: 6px;
    }
    .footer {
      display: flex;
      justify-content: flex-end;
      padding: 4px 15px 16px;
      .bk-button + .bk-button {
        margin-left: 8px;
      }
    }
    .bk-tag-input .key-node {
      border: 1px solid transparent!important;
      background: transparent!important;

      .tag {
        &.stable {
          color: #14a568;
          background-color: #e4faf0;
          & + .remove-key {
            background-color: #e4faf0;
          }
        }
        &.latest {
          color: $primaryFontColor;
          background-color: #edf4ff;
          & + .remove-key {
            background-color: #edf4ff;
          }
        }
        &.test {
          color: #fe9c00;
          background-color: #fff1db;
          & + .remove-key {
            background-color: #fff1db;
          }
        }
      }
      .remove-key {
        right: 1px;
        top: 0;
        width: 20px;
        height: 20px;
        line-height: 20px;
        color: #979ba5;
        background-color: #f0f1f5;
      }
    }
  }
</style>
