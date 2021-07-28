<template>
  <div class="pagination">
    <i18n path="分页文案" tag="div" class="pagination-left">
      <span class="count">{{ count }}</span>
      <div class="limit">
        <bk-select
          :clearable="false"
          v-model="realityLimit"
          @click="handleLimitChange">
          <bk-option
            v-for="(item ,index) in limitList"
            :key="index"
            :name="item"
            :id="item">
          </bk-option>
        </bk-select>
      </div>
    </i18n>
    <div class="pagination-right">
      <i class="nodeman-icon nc-arrow-left page-arrow mr5"></i>
      <input type="number" v-model="realityCurrent" class="page-current mr10" />
      <span class="separator">/</span>
      <span class="total ml10">{{ Math.ceil( count / limit ) }}</span>
      <i class="nodeman-icon nc-arrow-right page-arrow ml5"></i>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';

@Component({ name: 'pagination' })
export default class Pagination extends Vue {
  @Prop({ default: 0 }) private readonly count!: number;
  @Prop({ default: 0 }) private readonly current!: number;
  @Prop({ default: 20, validator: v => v > 0 }) private readonly limit!: number;
  @Prop({ default: () => [20, 50, 100], type: Array }) private readonly limitList!: number[];

  private realityLimit = this.limit;
  private realityCurrent = this.current;
  @Emit('limit-change')
  public handleLimitChange(newValue: string | number, oldValue: string | number) {
    return {
      newValue,
      oldValue,
    };
  }
}
</script>
<style lang="postcss" scoped>
.pagination {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  &-left {
    display: flex;
    align-items: center;
    .count {
      padding: 0 6px;
    }
    .limit {
      padding: 0 6px;
    }
  }
  &-right {
    display: flex;
    align-items: center;
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
      appearance: none;
    }
    input[type="number"] {
      appearance: textfield;
    }
    .page-arrow {
      height: 24px;
      width: 24px;
      font-size: 24px;
      color: #c4c6cc;
      cursor: pointer;
      &:hover {
        color: #3a84ff;
      }
    }
    .page-current {
      width: 36px;
      height: 32px;
      border: 1px solid #c4c6cc;
      border-radius: 2px;
      text-align: center;
      &:focus {
        border: 1px solid #3a84ff;
      }
    }
  }
}
</style>
