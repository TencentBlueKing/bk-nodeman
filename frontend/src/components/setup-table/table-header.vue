<template>
  <div class="setup-header">
    <span
      ref="tipSpan"
      :class="{
        'header-label': true,
        'header-label-required': required,
        'header-label-tips': Boolean(tips)
      }"
      @mouseenter="tipsShow"
      @mouseleave="tipsHide">
      {{ $t(label) }}
    </span>
    <bk-popover
      v-if="batch"
      theme="light batch-edit"
      trigger="manual"
      placement="bottom"
      ref="batch"
      :tippy-options="{ 'hideOnClick': false }"
      :on-show="handleOnShow"
      :on-hide="handleOnHide">
      <span
        v-bk-tooltips.top="{
          'content': $t('批量编辑', { title: '' }),
          'delay': [300, 0]
        }"
        class="batch-icon nodeman-icon nc-bulk-edit"
        :class="{ 'active': isActive }"
        @click="handleBatchClick"
        v-show="isBatchIconShow">
      </span>
      <template #content>
        <div class="batch-edit">
          <template v-if="type === 'password'">
            <div class="batch-edit-title">
              {{ $t('批量编辑', { title: $t('密码') }) }}
            </div>
            <div class="batch-edit-content" v-if="isShow">
              <input-type
                v-bind="{ type: 'password' }"
                v-model="value"
                @enter="handleBatchConfirm">
              </input-type>
              <div class="tip">{{ subTitle }}</div>
            </div>
            <div class="batch-edit-title">
              {{ $t('批量编辑', { title: $t('密钥') }) }}
            </div>
            <div class="batch-edit-content" v-if="isShow">
              <input-type
                v-bind="{ type: 'file' }"
                @upload-change="handleFileChange">
              </input-type>
              <div class="tip">{{ $t('仅对密钥认证生效') }}</div>
            </div>
          </template>
          <template v-else>
            <div class="batch-edit-title">
              {{ $t('批量编辑', { title: $t(label) }) }}
            </div>
            <div class="batch-edit-content" v-if="isShow">
              <input-type
                v-bind="{
                  type: type,
                  options: options,
                  multiple: multiple,
                  appendSlot: appendSlot,
                  placeholder
                }"
                v-model="value"
                @enter="handleBatchConfirm">
              </input-type>
              <div class="tip" v-if="subTitle">{{ subTitle }}</div>
            </div>
          </template>
          <div class="batch-edit-footer">
            <bk-button text ext-cls="footer-confirm" @click="handleBatchConfirm">{{ $t('确定') }}</bk-button>
            <bk-button text ext-cls="footer-cancel" class="ml20" @click="handleBatchCancel">{{ $t('取消') }}</bk-button>
          </div>
        </div>
      </template>
    </bk-popover>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Ref } from 'vue-property-decorator';
import { bus } from '@/common/bus';
import InputType from './input-type.vue';
import { IFileInfo } from '@/types';

@Component({
  name: 'table-header',
  components: {
    InputType,
  },
})

export default class TableHeader extends Vue {
  @Prop({ type: String, default: '' }) private readonly tips!: string; // 是否有悬浮提示
  @Prop({ type: String, default: '' }) private readonly label!: string; // 表头label
  @Prop({ type: Boolean, default: false }) private readonly required!: boolean; // 是否显示必填标识
  @Prop({ type: Boolean, default: false }) private readonly batch!: boolean; // 是否有批量编辑框
  @Prop({ type: Boolean, default: true }) private readonly isBatchIconShow!: boolean; // 是否显示批量编辑图标
  @Prop({ type: String, default: '' }) private readonly type!: string; // 批量编辑框类型
  @Prop({ type: String, default: '' }) private readonly subTitle!: string; // 批量编辑提示信息
  @Prop({ type: Array, default: () => ([]) }) private options!: Dictionary[]; // 下拉框数据源
  @Prop({ type: Boolean, default: false }) private readonly multiple!: boolean; // 是否支持多选
  @Prop({ type: String, default: '' }) private readonly placeholder!: string;
  @Prop({ type: String, default: '' }) private readonly appendSlot!: string;

  @Ref('batch') private readonly batchRef!: any;
  @Ref('tipSpan') private readonly tipSpan!: any;

  private isActive = false; // 当前批量编辑icon是否激活
  private value = '';
  private isShow = false;
  private fileInfo: null | IFileInfo = null; // 密钥信息
  private popoverInstance: any = null;

  private created() {
    bus.$on('batch-btn-click', this.hidePopover); // 只出现一个弹框
  }

  public handleBatchClick() {
    if (this.isActive) {
      this.handleBatchCancel();
    } else {
      this.batchRef && this.batchRef.instance.show();
      this.isActive = true;
      bus.$emit('batch-btn-click', this);
    }
  }
  @Emit('confirm')
  public handleBatchConfirm() {
    this.handleBatchCancel();
    return { value: this.value, fileInfo: this.fileInfo };
  }
  public handleBatchCancel() {
    this.isActive = false;
    this.batchRef && this.batchRef.instance.hide();
  }
  public handleOnShow() {
    this.value = '';
    this.isShow = true;
  }
  public handleOnHide() {
    this.isShow = false;
  }
  public hidePopover(instance: any) {
    if (instance === this) return;
    this.handleBatchCancel();
  }
  public handleFileChange(fileInfo: IFileInfo) {
    this.fileInfo = fileInfo;
  }
  public tipsShow() {
    if (this.tips && !this.popoverInstance) {
      const ref = this.tipSpan;
      this.popoverInstance = this.$bkPopover(ref, {
        content: this.tips,
        trigger: 'manual',
        arrow: true,
        theme: 'light default',
        maxWidth: 200,
        sticky: true,
        duration: [275, 0],
        interactive: true,
        boundary: 'window',
        placement: 'top',
        hideOnClick: false,
        onHidden: () => {
          this.popoverInstance && this.popoverInstance.destroy();
        },
      });
      this.popoverInstance && this.popoverInstance.show();
    }
  }
  public tipsHide() {
    this.popoverInstance && this.popoverInstance.hide();
    this.popoverInstance = null;
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  .setup-header {
    font-weight: normal;
    text-align: left;

    @mixin layout-flex row, center;
    .header-label {
      position: relative;
      display: flex;
      line-height: 16px;
      white-space: nowrap;
      &-required {
        margin-right: 6px;
        &::after {
          content: "*";
          color: #ff5656;
          position: absolute;
          top: 2px;
          right: -7px;
        }
      }
      &-tips {
        border-bottom: 1px dashed #c4c6cc;
        cursor: default;
      }
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
</style>
