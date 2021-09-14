<template>
  <ul class="rule-type">
    <li v-for="(item, index) in list" v-test.policy="item.id"
        :key="index"
        :class="[
          'item',
          { 'ml20': index > 0 },
          { 'active': active === item.id },
          { 'disabled': !!item.disabled }
        ]"
        v-bk-tooltips="{
          content: item.tips,
          disabled: !item.disabled || !item.tips
        }"
        @click="handleItemClick(item)">
      <div class="item-left">
        <i :class="[
          item.icon.indexOf('bk-icon') > -1
            ? 'bk-icon'
            : 'nodeman-icon',
          item.icon]"></i>
      </div>
      <div class="item-right">
        <span class="title">{{ item.title }}</span>
        <span class="mt5 desc">{{ item.desc }}</span>
      </div>
      <span class="item-check" v-if="active === item.id"></span>
    </li>
  </ul>
</template>
<script lang="ts">
import { Component, Vue, Prop, Emit, Watch, Model } from 'vue-property-decorator';
import { IRuleType } from '@/types/plugin/plugin-type';

@Component({ name: 'rule-type' })
export default class RuleType extends Vue {
  @Model('change', { default: 'oldRule', type: String }) private readonly active!: string;
  @Prop({ default: false, type: Boolean }) private readonly disabledOldRule!: boolean;

  private list: IRuleType[] = [];

  @Watch('disabledOldRule')
  private handleDisabledStatusChange(disabled: boolean) {
    const data = this.list.find(item => item.id === 'oldRule');
    data && (data.disabled = disabled);
  }

  private created() {
    this.list = [
      {
        id: 'oldRule',
        icon: 'nc-state',
        title: this.$t('已有策略'),
        desc: this.$t('基于已有的策略调整目标'),
        disabled: this.disabledOldRule,
        tips: this.$t('该插件暂无部署策略'),
      },
      {
        id: 'newRule',
        icon: 'bk-icon icon-plus-line',
        title: this.$t('新建策略'),
        desc: this.$t('已有策略不适用继续新建'),
        disabled: false,
      },
    ];
  }

  @Emit('change')
  public handleItemClick(item: IRuleType) {
    if (item.disabled) return this.active;

    return item.id;
  }
}
</script>
<style lang="postcss" scoped>
.rule-type {
  display: flex;
  .item {
    display: flex;
    height: 64px;
    width: 230px;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    cursor: pointer;
    position: relative;
    &.active {
      border-color: #3a84ff;
      .item-left {
        border-color: #3a84ff;
        background: #e1ecff;
        color: #3a84ff;
      }
    }
    &.disabled {
      border-color: #dcdee5;
      cursor: not-allowed;
      .item-left {
        border-color: #dcdee5;
        color: #dcdee5;
      }
      .title {
        color: #c4c6cc;
      }
      .desc {
        color: #c4c6cc;
      }
    }
    &-left {
      flex: 0 0 50px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      border-right: 1px solid #c4c6cc;
      background: #fafbfd;
      color: #979ba5;
    }
    &-right {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 10px 14px;
      background: #fff;
      .title {
        line-height: 19px;
        font-size: 14px;
        color: #313238;
      }
      .desc {
        line-height: 16px;
        color: #979ba5;
      }
    }
    .item-check {
      position: absolute;
      width: 0;
      height: 0;
      right: 0;
      border-top: 16px solid #3a84ff;
      border-right: 16px solid #3a84ff;
      border-bottom: 16px solid transparent;
      border-left: 16px solid transparent;
      &::after {
        content: "\00a0";
        display: inline-block;
        border: 2px solid #fff;
        border-top-width: 0;
        border-right-width: 0;
        width: 8px;
        height: 4px;
        transform: rotate(-50deg);
        position: absolute;
        top: -10px;
      }
    }
  }
}
</style>
