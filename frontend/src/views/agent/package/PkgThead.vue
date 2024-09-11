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
              searchable
              has-delete-icon
              use-group
              trigger="focus"
              :list="options"
              :placeholder="$t('请输入或选择')"
              :tag-tpl="tagTpl"
              v-model="value"
              :collapse-tags="true"
              @blur="handleBlur"
              @inputchange="handleInputchange" />
            <div class="create-tag-pop" v-if="popShow" @click="createTag">
              <div class="create-tag-box">
                <i18n path="新建标签" class="create-tag">
                  <span>{{ tag }}</span>
                </i18n>
              </div>
            </div>
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
import { IPkgTagOpt, PkgType} from '@/types/agent/pkg-manage';
import { AgentStore } from '@/store';
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
    active: {
      type: String as PropType<PkgType>,
      default: 'gse_agent',
    }
  },
  emits: ['confirm'],
  setup(props, { emit }) {
    const proxy = getCurrentInstance()?.proxy;

    const batchRef = ref<any>();
    const tipSpanRef = ref<any>();
    const tipRef = ref<any>();
    const tag = ref<any>();

    const state = reactive<{
      isActive: boolean;
      value: string[];
      isShow: boolean;
      popShow: boolean; // 输入未匹配标签时候展示
    }>({
      isActive: false, // 当前批量编辑icon是否激活
      value: [],
      isShow: false,
      popShow: false,
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

    // 处理输入值更改时候的option效果
    const handleInputchange = (value: string) => {
      const index = props.options.findIndex((item: any) => item.children.find((child: any) => child.name === value)) || -1;
      if (index === -1 && value && !state.value.includes(value)) {
        state.popShow = true;
        tag.value = value;
      } else {
        state.popShow = false;
        tag.value = '';
      }
    };
    // 输入框失去焦点
    const handleBlur = () => {
      state.popShow = false;
      tag.value = '';
    }

    // 新建标签
    const createTag = async () => {
      const backup = tag.value;
      tag.value = '';
      state.popShow = false;
      const customLabels: any= props.options.find((item: any) => item.id === 'custom');
      customLabels?.children.push({
        id: backup,
        name: backup,
        className: '',
      });
      
      state.value.push(backup);
      await AgentStore.apiPkgCreateTags({ project: props.active, tag_descriptions: state.value });
    }

    return {
      ...toRefs(props),
      ...toRefs(state),

      batchRef,
      tipSpanRef,
      tipRef,
      tag,

      handleBatchClick,
      handleBatchConfirm,
      handleBatch,
      handleBatchCancel,
      handleOnShow,
      handleOnHide,
      hidePopover,
      tagTpl,
      handleInputchange,
      handleBlur,
      createTag,
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

  .batch-edit-content {
    display: flex;
    flex-direction: column;
    .create-tag-pop {
      cursor: pointer;
      width: 100%;
      margin-top: 4px;
      transition-duration: 325ms;
      height: 40px;
      background: #fff;
      border: 1px solid #DCDEE5;
      box-shadow: 0 2px 6px 0 #0000001a;
      border-radius: 2px;
      .create-tag-box {
        width: 100%;
        height: 32px;
        margin: 4px 0;
        line-height: 32px;
        background: #F5F7FA;
        .create-tag {
          color: #63656E;
          margin-left: 24px;
          font-size: 12px;
          span {
            color: #3A84FF;
          }
        }
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
