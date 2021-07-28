<template>
  <bk-dialog
    :value="value"
    header-position="left"
    :title="title"
    width="800"
    @value-change="handleValueChange"
    @confirm="confirm"
    @cancel="cancel">
    <template #default>
      <bk-table :data="data" max-height="464" v-if="data.length && value" ref="table">
        <bk-table-column label="IP" prop="ip" width="180"></bk-table-column>
        <bk-table-column :label="$t('过滤原因')" prop="msg" show-overflow-tooltip></bk-table-column>
      </bk-table>
    </template>
    <template #footer>
      <div class="footer">
        <bk-button @click="handleFilterExport">{{ $t('导出') }}</bk-button>
        <div class="footer-right">
          <bk-button theme="primary" @click="handleFilterConfirm">{{ $t('确定') }}</bk-button>
        </div>
      </div>
    </template>
  </bk-dialog>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Model, Watch, Ref } from 'vue-property-decorator';
import { IFilterDialogRow } from '@/types/agent/agent-type';

@Component({ name: 'filter-dialog' })

export default class FilterDialog extends Vue {
  @Model('change', { type: Boolean, default: false }) private value!: boolean;

  @Prop({ type: String, default: '' }) private readonly title!: string;
  @Prop({ type: Array, default: () => ([]) }) private readonly list!: IFilterDialogRow[];

  @Ref('table') private readonly table: any;

  private data: IFilterDialogRow[] = JSON.parse(JSON.stringify(this.list));

  @Watch('list')
  public handleListChange(v: IFilterDialogRow[]) {
    this.data = JSON.parse(JSON.stringify(v));
  }
  @Emit('change')
  public handleValueChange(v: boolean) {
    return v;
  }
  @Emit('confirm')
  public confirm() {
    return this.data;
  }
  @Emit('cancel')
  public cancel() {
    return this.data;
  }
  @Emit('filter-confirm')
  public handleFilterConfirm() {
    this.handleValueChange(false);
    return this.data;
  }
  @Emit('filter-export')
  public handleFilterExport() {
    const elt = this.table.$el;
    import('xlsx').then((XLSX) => {
      // @ts-ignore: Unreachable code error
      const wb = XLSX.utils.table_to_book(elt, { sheet: this.$t('过滤列表') });
      XLSX.writeFile(wb, `${this.$t('过滤列表')}.xlsx`);
    });
    this.handleValueChange(false);
    return this.data;
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  >>> .bk-dialog-body {
    padding: 0;
  }
  >>> .bk-dialog-footer {
    border-top: 0;
  }
  >>> .is-first {
    .cell {
      padding-left: 24px;
    }
  }
  .footer {
    @mixin layout-flex row, center, space-between;
    .footer-right {
      @mixin layout-flex row;
    }
  }
</style>
