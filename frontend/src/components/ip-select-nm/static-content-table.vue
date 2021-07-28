<template>
  <bk-table
    :data="data"
    :outer-border="false"
    :header-border="false"
    :row-class-name="handleGetRowClass"
    :pagination="pagination"
    @page-change="handlePagetionChage(arguments, 'page')"
    @page-limit-change="handlePagetionChage(arguments, 'limit')"
    class="static-table">
    <bk-table-column
      :render-header="renderHeader"
      width="70"
      v-if="selection">
      <template #default="{ row }">
        <div v-bk-tooltips="{
          placement: 'right',
          content: getTooltipsContent(row),
          disabled: !showStatus,
          delay: 500
        }">
          <bk-checkbox
            v-model="row.selection"
            :disabled="row.disabled">
          </bk-checkbox>
          <span v-if="showStatus">
            <i class="nodeman-icon nc-minus-line"
               v-if="isDeleteHost(row)"></i>
            <i class="nodeman-icon nc-plus-line"
               v-else-if="isAddHost(row)"></i>
          </span>
        </div>
      </template>
    </bk-table-column>
    <bk-table-column :label="$t('主机IP')" prop="inner_ip">
      <template #default="{ row }">
        <span v-bk-tooltips="{
          content: row.disabled_msg,
          disabled: !row.disabled
        }">{{ row.inner_ip }}</span>
      </template>
    </bk-table-column>
    <bk-table-column :label="$t('Agent状态')" prop="status">
      <template #default="{ row }">
        <div class="col-status">
          <span :class="'status-mark status-' + row.status.toLocaleLowerCase()"></span>
          <span>{{ statusMap[row.status] }}</span>
        </div>
      </template>
    </bk-table-column>
    <bk-table-column :label="$t('云区域')" prop="bk_cloud_name"></bk-table-column>
    <!-- <bk-table-column :label="$t('主机名')" prop="bk_host_name"></bk-table-column> -->
    <bk-table-column :label="$t('操作系统')" prop="os_type">
      <template #default="{ row }">
        <span>{{ osMap[row.os_type] || '--' }}</span>
      </template>
    </bk-table-column>
    <bk-table-column width="80" :label="$t('操作')" v-if="operate">
      <template #default="{ row }">
        <bk-button text @click="handleRemove(row)">{{ $t('移除') }}</bk-button>
      </template>
    </bk-table-column>
  </bk-table>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Watch } from 'vue-property-decorator';
import ColumnCheck from '@/views/agent/components/column-check.vue';
import { CreateElement } from 'vue';
import { IPagination } from '@/types/plugin/plugin-type';

@Component({ name: 'static-content-table' })
export default class StaticContentTable extends Vue {
  @Prop({ default: true }) private readonly selection!: boolean;
  @Prop({ default: false }) private readonly operate!: boolean;
  @Prop({ default: () => [] }) private readonly data!: any[];
  @Prop({ default: true }) private readonly showStatus!: boolean;
  @Prop({ type: Object, default: () => ({}) }) private readonly pagination!: IPagination;

  private selections: (string | number)[] = [];
  private statusMap = {
    RUNNING: window.i18n.t('正常'),
    TERMINATED: window.i18n.t('异常'),
    NOT_INSTALLED: window.i18n.t('未安装'),
  };
  private osMap = {
    LINUX: 'Linux',
    WINDOWS: 'Windows',
    AIX: 'AIX',
  };

  @Watch('data', { immediate: true, deep: false })
  private handleDataChange() {
    this.selections = this.data.reduce<(string | number)[]>((pre, cur) => {
      if (cur.selection) {
        pre.push(cur.id);
      }
      return pre;
    }, []);
  }
  public handleGetRowClass({ row }: { row: any }) {
    if (row.disabled) {
      return 'row-disabled';
    }
  }

  @Emit('remove')
  public handleRemove(row: any) {
    return row;
  }
  @Emit('paginationChange')
  public handlePagetionChage(arg: number[], type: 'page' | 'limit') {
    if (type === 'limit') {
      return { page: 1, pagesize: arg[0] };
    }
    return { page: arg[0], pagesize: this.pagination.limit };
  }

  public renderHeader(h: CreateElement) {
    return h(ColumnCheck, {

    });
  }
  public isAddHost(row: any) {
    return !this.selections.includes(row.id) && !!row.selection;
  }
  public isDeleteHost(row: any) {
    return this.selections.includes(row.id) && !row.selection;
  }
  public getTooltipsContent(row: any) {
    if (this.isDeleteHost(row)) {
      return this.$t('待卸载，点击恢复');
    }
    if (!this.isAddHost(row) && row.selection) {
      return this.$t('已部署，取消后将会卸载');
    }
    return '';
  }
}
</script>
<style lang="postcss" scoped>
.nc-minus-line {
  color: #ea3636;
}
.nc-plus-line {
  color: #3a84ff;
}
.static-table {
  border-bottom: 1px solid #dcdee5;
  &::before {
    height: 0;
  }
  >>> th {
    background-color: #f5f6fa;
  }
}
>>> .row-disabled {
  color: #dcdee5;
}
</style>
