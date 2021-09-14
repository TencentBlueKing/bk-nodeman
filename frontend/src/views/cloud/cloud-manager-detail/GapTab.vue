<template>
  <div class="rule-step">
    <div class="step-item" v-for="(item, index) in list" :key="index" @click="handleClickStep(item)">
      <bk-popover placement="top" :disabled="!showTips">
        <div
          v-test="'channelItem'"
          :class="['step', {
            active: active === item.id,
            controllable: controllable,
            disabled: !controllable && active !== item.id
          }]">
          <div class="step-content">
            <span class="number" v-if="item.icon || showIcon">{{ item.icon }}</span>
            <span class="title">{{ item.label }}</span>
            <i v-if="item.error" class="bk-icon icon-exclamation-circle-shape error"></i>
          </div>
        </div>
      </bk-popover>
    </div>
    <div class="add-btn" v-test="'addChannel'" v-if="addable" @click="handleAddClick">
      <bk-button class="tab-loading" theme="default" v-if="loading" loading />
      <slot v-else name="add">
        <i class="nodeman-icon nc-plus-line"></i>
        <span class="title">{{ $t('新建安装通道') }}</span>
      </slot>
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Prop, Vue, ModelSync, Emit } from 'vue-property-decorator';
interface IStep {
  label: string
  id: number | string
  icon: number
  description?: string
  com: string,
  disabled?: boolean
  error?: boolean
}

@Component
export default class GapTab extends Vue {
  // @Prop({ default: 'tab', type: String }) private readonly mode!: 'tab' | 'step'
  @Prop({ default: false, type: Boolean }) private readonly addable!: boolean;
  @Prop({ default: () => [], type: Array }) private readonly list!: IStep[];
  @Prop({ default: true, type: Boolean }) private readonly controllable!: boolean;
  @Prop({ default: false, type: Boolean }) private readonly showTips!: boolean;
  @Prop({ default: false, type: Boolean }) private readonly showIcon!: boolean;
  @Prop({ default: false, type: Boolean }) private readonly loading!: boolean;
  @ModelSync('value', 'change', { default: 'default', type: [Number, String] }) private active!: number | string;

  @Emit('change')
  public handleChangeStep(item: IStep) {
    return item.id;
  }
  @Emit('add-tab')
  public handleAddClick() {
    return true;
  }

  public handleClickStep(item: IStep) {
    if (!this.controllable) return;

    this.handleChangeStep(item);
  }
}
</script>
<style lang="postcss" scoped>
  .rule-step {
    position: relative;
    display: flex;
    align-items: center;
    padding: 0 24px;
    &::after {
      position: absolute;
      left: 0;
      bottom: 0;
      content: "";
      display: block;
      width: 100%;
      border-bottom: 1px solid #dcdee5;
    }
    & > div {
      overflow: hidden;
      z-index: 5;
    }
    .step {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 42px;
      padding: 0 24px;/* width: 220px; */
      background: #e1e3eb;
      border-top-left-radius: 6px;
      border-top-right-radius: 6px;
      font-size: 14px;
      .step-content {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        position: relative;
      }
      &.active {
        background: #fff;
        border: 1px solid #dcdee5;
        border-bottom: 1px solid #fff;
        box-shadow: 0px 0px 6px 0px rgba(0,0,0,.04);/* color: #313238;
        font-weight: 700; */
        .number {
          border: 1px solid #313238;
        }
      }
      &.controllable {
        cursor: pointer;
      }
      &.disabled {
        cursor: not-allowed;
      }
      .number {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 1px solid #63656e;
        transform: scale(.8);
        margin-right: 2px;
      }
      .title {
        line-height: 16px;
      }
      .bk-icon {
        position: absolute;
        top: 3px;
        right: -19px;
        &.error {
          color: #ea3636;
        }
      }
    }
    .tab-loading {
      line-height: 1;
      border: 0;
      background: transparent;
    }
    .add-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 42px;
      padding: 0 22px;
      font-size: 14px;
      cursor: pointer;
      i {
        margin-right: 6px;
        font-size: 16px;
        color: #3a84ff;
      }
    }
    .step-item + .step-item {
      margin-left: 10px;
    }
  }
</style>
