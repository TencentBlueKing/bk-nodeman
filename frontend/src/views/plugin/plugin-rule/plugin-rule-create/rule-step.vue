<template>
  <div class="rule-step">
    <div v-for="(step, index) in steps" :key="index" @click="handleClickStep(step)">
      <bk-popover placement="top" :disabled="!showTips">
        <div
          :class="['step mr10', {
            active: curStep === step.icon,
            controllable: controllable,
            disabled: !controllable && curStep !== step.icon
          }]">
          <div class="step-content">
            <span class="number">
              {{ step.icon }}
            </span>
            <span class="title">{{ step.title }}</span>
            <i v-if="step.error" class="bk-icon icon-exclamation-circle-shape error"></i>
          </div>
        </div>
        <template #content>
          <div v-if="showTips">
            <slot name="disable-tips">
              <p>{{ $t('新建流程中只允许点击下一步') }}</p>
              <p>{{ $t('后续编辑可快速切换TAB') }}</p>
            </slot>
          </div>
        </template>
      </bk-popover>
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Prop, Vue, ModelSync, Emit } from 'vue-property-decorator'
import { IStep } from '@/types/plugin/plugin-type'

@Component
export default class RuleStep extends Vue {
  @Prop({ default: () => [], type: Array }) private readonly steps!: IStep[]
  @Prop({ default: true, type: Boolean }) private readonly controllable!: boolean
  @Prop({ default: true, type: Boolean }) private readonly showTips!: boolean
  @ModelSync('value', 'change', { default: 1, type: Number }) private curStep!: number | string

  @Emit('change')
  private handleChangeStep(item: IStep) {
    return item.icon
  }

  private handleClickStep(item: IStep) {
    if (!this.controllable) return

    this.handleChangeStep(item)
  }
}
</script>
<style lang="postcss" scoped>
.rule-step {
  position: relative;
  display: flex;
  align-items: center;
  padding: 0 25px;
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
    width: 220px;
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
      box-shadow: 0px 0px 6px 0px rgba(0,0,0,.04);
      color: #313238;
      font-weight: 700;
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
}
</style>
