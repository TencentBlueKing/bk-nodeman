<template>
  <div class="wrapper">
    <div class="content">
      <bk-input
        type="textarea"
        :placeholder="$t('请输入筛选条件，模糊匹配条件之间用 | 分隔')"
        v-model="ruleName">
      </bk-input>
    </div>
    <div class="footer">
      <bk-button class="btn mr10" text @click="handleConfirm">{{ $t('确定') }}</bk-button>
      <bk-button class="btn" text @click="handleReset">{{ $t('重置') }}</bk-button>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Emit } from 'vue-property-decorator';

@Component({ name: 'table-filter' })
export default class TableFilter extends Vue {
  public ruleName = '';
  @Emit('confirm')
  public handleConfirm() {
    return this.ruleName;
  }

  @Emit('reset')
  public handleReset() {
    return this.ruleName;
  }
}
</script>
<style lang="postcss" scoped>
.wrapper {
  width: 280px;
  .content {
    padding: 12px 15px;
    >>> .bk-form-textarea {
      height: 56px;
      min-height: 56px;
      width: 248px;
    }
  }
  .footer {
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 20px;
    border-top: 1px solid #f0f1f5;
    .btn {
      font-size: 12px;
    }
  }
}
</style>
