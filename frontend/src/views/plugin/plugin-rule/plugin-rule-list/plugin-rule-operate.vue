<template>
  <div class="rule-operate">
    <div class="rule-operate-left">
      <bk-button v-test="'addPolicy'" theme="primary" v-authority="{
        active: !createdOperate, // mixin
        apply_info: [
          { action: 'strategy_view' },
          { action: 'strategy_create' }
        ]
      }" @click="handleAddRule">{{ $t('新建策略') }}</bk-button>
      <bk-biz-select
        v-model="biz"
        class="ml10 select"
        action="strategy_view"
        :auto-request="autoRequest"
        :placeholder="$t('全部业务')"
        @change="handleBizChange">
      </bk-biz-select>
    </div>
    <div class="rule-operate-right">
      <bk-input
        v-test="'searchInput'"
        :placeholder="$t('搜索策略插件')"
        clearable
        :right-icon="'bk-icon icon-search'"
        v-model.trim="searchValue"
        @change="handleValueInput">
      </bk-input>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Emit, Prop } from 'vue-property-decorator';
import { MainStore } from '@/store';

@Component({ name: 'plugin-rule-operate' })
export default class PluginRuleOperate extends Vue {
  @Prop({ type: String, default: '' }) private readonly searchValues!: string;
  @Prop({ type: Boolean, default: false }) private readonly createdOperate!: boolean; // 创建权限

  private biz: number[] = [];
  private searchValue = this.searchValues;
  private strategy = '';

  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  private get autoRequest() {
    return !MainStore.permissionSwitch;
  }

  @Emit('value-change')
  private handleValueChange(newVal: string) {
    return newVal;
  }
  @Emit('strategy-change')
  private handleStrategyChange() {
    return this.strategy;
  }

  @Emit('biz-change')
  private handleBizChange(biz: number[]) {
    return biz;
  }

  private created() {
    this.biz = this.selectedBiz;
  }

  private handleAddRule() {
    this.$router.push({ name: 'chooseRule' });
  }
  private handleValueInput(newVal: string) {
    if (newVal.trim() !== this.searchValues.trim()) {
      this.handleValueChange(newVal.trim());
    }
  }
}
</script>
<style lang="postcss" scoped>
.rule-operate {
  display: flex;
  justify-content: space-between;
  &-left {
    display: flex;
    >>> .bk-select {
      background: #fff;
    }
    .select {
      width: 240px;
    }
  }
  &-right {
    flex-basis: 500px;
  }
}
</style>
