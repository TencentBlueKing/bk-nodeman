<template>
  <div class="task-list-table-wrapper">
    <section class="task-table" v-bkloading="{ isLoading: loading }">
      <bk-table
        ref="agentTable"
        :data="tableList"
        :pagination="pagination"
        :limit-list="pagination.limitList"
        :row-style="getRowStyle"
        :max-height="windowHeight - 230"
        :row-class-name="handlerRowClassName"
        @sort-change="sortHandle"
        @row-click="detailHandle"
        @page-change="pageChange"
        @page-limit-change="limitChange">
        <bk-table-column :label="$t('任务ID')" prop="job_id" :resizable="false">
          <template #default="{ row }">
            <a href="javascript: " class="primary">{{ row.id }}</a>
          </template>
        </bk-table-column>
        <bk-table-column
          class-name="biz-column"
          prop="bkBizScopeDisplay"
          show-overflow-tooltip
          :label="$t('业务')">
          <template #default="{ row }">
            {{ row.bkBizScopeDisplay && row.bkBizScopeDisplay.length ? row.bkBizScopeDisplay.join(',') : '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          prop="step_type"
          min-width="80"
          :label="$t('任务类型')"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            {{ row.stepTypeDisplay | filterEmpty }}
          </template>
        </bk-table-column>
        <bk-table-column
          prop="op_type"
          min-width="110"
          :label="$t('操作类型')"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            {{ row.opTypeDisplay | filterEmpty }}
          </template>
        </bk-table-column>
        <bk-table-column
          prop="policy_name"
          min-width="140"
          show-overflow-tooltip
          :label="$t('部署策略')"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            {{ row.policyName | filterEmpty }}
          </template>
        </bk-table-column>
        <bk-table-column
          prop="created_by"
          :label="$t('执行者')"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            {{ row.createdBy ? row.createdBy : '--' }}
          </template>
        </bk-table-column>
        <bk-table-column width="185" :label="$t('执行时间')" prop="startTime">
          <template #default="{ row }">
            {{ row.startTime | filterTimezone }}
          </template>
        </bk-table-column>
        <bk-table-column align="right" :label="$t('总耗时')" prop="costTime" min-width="90">
          <template #default="{ row }">{{ takesTimeFormat(row.costTime) }} </template>
        </bk-table-column>
        <bk-table-column min-width="20" :resizable="false"></bk-table-column>
        <bk-table-column
          prop="status"
          min-width="115"
          :label="$t('执行状态')"
          :resizable="false"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            <div class="col-execution">
              <loading-icon v-if="row.status === 'running'"></loading-icon>
              <span v-else :class="`execut-mark execut-${ row.status }`"></span>
              <span class="execut-text" :title="titleStatusMap[row.status]">{{ titleStatusMap[row.status] }}</span>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('总数成功失败忽略')" min-width="190">
          <template #default="{ row }">
            <template v-if="row.statistics">
              <span class="num">{{ row.statistics.totalCount || 0 }}</span>/
              <a class="success num"
                 @click.stop="detailHandle(row, 'success')">{{ row.statistics.successCount || 0 }}</a>/
              <a class="failed num"
                 @click.stop="detailHandle(row, 'failed')">{{ row.statistics.failedCount || 0 }}</a>/
              <a class="ignored num"
                 @click.stop="detailHandle(row, 'ignored')">{{ row.statistics.ignoredCount || 0 }}</a>
            </template>
            <span v-else>--</span>
          </template>
        </bk-table-column>

        <NmException
          slot="empty"
          :type="tableEmptyType"
          @empty-clear="emptySearchClear"
          @empty-refresh="emptyRefresh" />
      </bk-table>
    </section></div>
</template>

<script lang="ts">
import { Component, Prop, Emit, Mixins } from 'vue-property-decorator';
import { IPagination, ISearchItem } from '@/types';
import { IHistory } from '@/types/task/task';
import HeaderRenderMixin from '@/components/common/header-render-mixins';
import { isEmpty, takesTimeFormat } from '@/common/util';
import { MainStore } from '@/store/index';

@Component({ name: 'task-list-table' })
export default class TaskListTable extends Mixins(HeaderRenderMixin) {
  @Prop({ type: Object, default: () => ({
    limit: 50,
    current: 1,
    count: 0,
    limitList: [50, 100, 200],
  }) }) private readonly pagination!: IPagination;
  @Prop({ type: Array, default: () => ([]) }) private readonly tableList!: Array<IHistory>;
  @Prop({ type: Boolean, default: false }) private readonly loading!: boolean;
  @Prop({ type: Array, default: () => ([]) }) private readonly highlight!: number[];
  @Prop({ type: Array, default: () => ([]) }) public readonly filterData!: ISearchItem[];
  @Prop({ type: Array, default: () => ([]) }) public readonly searchSelectValue!: ISearchItem[];

  private titleStatusMap = {
    pending: window.i18n.t('等待执行'),
    running: window.i18n.t('正在执行'),
    success: window.i18n.t('执行成功'),
    failed: window.i18n.t('执行失败'),
    part_failed: window.i18n.t('部分失败'),
    stop: window.i18n.t('已终止'),
    terminated: window.i18n.t('已终止'),
  };

  private get windowHeight() {
    return MainStore.windowHeight;
  }
  private get tableEmptyType() {
    return this.searchSelectValue.length ? 'search-empty' : 'empty';
  }

  @Emit('pagination-change')
  public handlePaginationChange({ type, value }: { type: string, value: string | number }) {
    return { type, value };
  }
  @Emit('sort-change')
  public sortHandle({ prop, order }: { prop: string, order: string }) {
    return { prop, order };
  }

  // 分页
  public pageChange(page: number) {
    this.handlePaginationChange({ type: 'current', value: page || 1 });
  }
  // 分页条数
  public limitChange(limit: number) {
    this.handlePaginationChange({ type: 'limit', value: limit || 1 });
  }
  public isEmptyCell(cell: number) {
    return !isEmpty(cell);
  }
  public getRowStyle() {
    return { cursor: 'pointer' };
  }
  // 耗时格式化
  public takesTimeFormat(seconds: number) {
    return takesTimeFormat(seconds);
  }
  // 跳转详情
  public detailHandle(row: IHistory, status: string) {
    this.$router.push({
      name: 'taskDetail',
      params: {
        taskId: row.id,
        status: status && typeof status === 'string' ? status.toUpperCase() : '',
      },
    });
  }
  public handlerRowClassName({ row }: { row: IHistory }) {
    return this.highlight.length && this.highlight.includes(row.id) ? 'highlight-row' : '';
  }
}
</script>

<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.task-list-table-wrapper {
  .task-table {
    margin-top: 14px;
    .num {
      padding-right: 4px;
    }
    .primary {
      color: #3a84ff;
    }
    .success {
      color: #2dcb56;
    }
    .failed {
      color: #ea3636;
    }
    .ignored {
      color: #ff9c01;
    }
    >>> .biz-column .cell {
      padding-left: 0;
    }
    >>> .highlight-row {
      animation: show-highlight 1.2s;

      @keyframes show-highlight {
        0% { background: #fff; }
        20% { background: #fff; }
        40% { background: #f0f5ff; }
        60% { background: #fff; }
        80% { background: #f0f5ff; }
        100% { background: #fff; }
      }
    }
  }
}
</style>
