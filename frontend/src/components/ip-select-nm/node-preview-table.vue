<template>
  <bk-table
    :data="data"
    :outer-border="false"
    :header-border="false"
    :show-header="false"
    @page-change="handlePagetionChage(arguments, 'page')"
    @page-limit-change="handlePagetionChage(arguments, 'limit')"
    class="preview-table">
    <bk-table-column>
      <template #default="{ row }">
        {{ row.path || row.name || '--' }}
      </template>
    </bk-table-column>
    <bk-table-column>
      <template #default="{ row }">
        <i18n path="节点统计">
          <span class="total">{{ row.total || 0 }}</span>
          <span class="running">{{ row.RUNNING || 0 }}</span>
          <span class="terminated">{{ row.TERMINATED || 0 }}</span>
          <span class="not_installed">{{ row.NOT_INSTALLED || 0 }}</span>
        </i18n>
      </template>
    </bk-table-column>
    <bk-table-column width="80" v-if="operate">
      <template #default="{ row }">
        <bk-button text @click="handleRemove(row)">{{ $t('移除') }}</bk-button>
      </template>
    </bk-table-column>
  </bk-table>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import { IPagination } from '@/types';

@Component({ name: 'node-preview-table' })
export default class NodePreviewTable extends Vue {
  @Prop({ type: Boolean, default: false }) private readonly operate!: boolean;
  @Prop({ type: Object, default: () => ({}) }) private readonly pagination!: IPagination;
  @Prop({ default: () => [] }) private readonly data!: any[];

  @Emit('paginationChange')
  public handlePagetionChage(arg: number[], type: 'page' | 'limit') {
    if (type === 'limit') {
      return { page: 1, pagesize: arg[0] };
    }
    return { page: arg[0], pagesize: this.pagination.limit };
  }
}
</script>
<style lang="postcss" scoped>
.preview-table::before {
  height: 0;
}
.total {
  color: #3a84ff
}
.running {
  color: #3fc06d;
}
.terminated {
  color: #ea3636;
}
.not_installed {
  color: #b2b5bd;
}
</style>
