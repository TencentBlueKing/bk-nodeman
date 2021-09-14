<template>
  <section class="task-detail-table" v-bkloading="{ isLoading: loading }" v-test="'detailTable'">
    <bk-table
      row-key="instanceId"
      :data="tableList"
      :pagination="pagination"
      :limit-list="pagination.limitList"
      :class="`${ fontSize }`"
      :max-height="tableHeight"
      @page-change="pageChange"
      @page-limit-change="limitChange"
      @select="handleSelect"
      @select-all="handleSelect">
      <!-- <bk-table-column
        class-name="row-select"
        type="selection"
        width="40"
        :resizable="false"
        :reserve-selection="true"
        :selectable="getSelectAbled">
      </bk-table-column> -->
      <bk-table-column class-name="row-ip" label="IP" prop="innerIp" :resizable="false"></bk-table-column>
      <bk-table-column :label="$t('云区域')" prop="bkCloudName" :resizable="false"></bk-table-column>
      <bk-table-column min-width="100" :label="$t('业务')" prop="bkBizName" :resizable="false"></bk-table-column>
      <bk-table-column min-width="100" :label="$t('操作类型')" prop="opTypeDisplay" :resizable="false"></bk-table-column>
      <bk-table-column
        v-if="operateHost === 'Plugin'"
        min-width="100"
        :label="$t('目标版本')"
        :resizable="false">
        <template #default="{ row }">
          {{ row.targetVersion | filterEmpty }}
        </template>
      </bk-table-column>
      <bk-table-column v-else min-width="100" :label="$t('安装方式')" prop="isManual" :resizable="false">
        <template #default="{ row }">
          {{ installTypeCell(row.isManual) }}
        </template>
      </bk-table-column>
      <bk-table-column min-width="100" :label="$t('耗时')" prop="costTime" :resizable="false">
        <template #default="{ row }">
          {{ takesTimeFormat(row.costTime) }}
        </template>
      </bk-table-column>
      <bk-table-column
        prop="status"
        :label="$t('执行状态')"
        min-width="220"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          <div
            class="col-execution"
            v-if="'running' === row.status && showCommindBtn && row.step === commandStepText">
            <span class="execut-mark execut-ignored"></span>
            <i18n tag="span" path="等待手动操作查看" class="execut-text">
              <bk-button text theme="primary" @click="handleRowView('viewCommind',row)">
                {{ $t('操作指引') }}
              </bk-button>
            </i18n>
          </div>
          <!-- is_running 区分已忽略且正在别的任务下执行的情况 -->
          <div class="col-execution" v-else>
            <loading-icon v-if="row.status === 'running'"></loading-icon>
            <span v-else :class="`execut-mark execut-${ row.status }`"></span>
            <span
              v-if="row.status === 'filtered' || row.status === 'ignored'"
              :class="['execut-text', { 'has-icon': row.exception && row.exception === 'is_running' }]"
              :title="filteredTitle(row)"
              @click.stop="handleRowView('filterrd', row)">
              {{ `${titleStatusMap[row.status]} ` }}
              ({{ row.statusDisplay | filterEmpty }}
              <i
                v-if="row.exception && row.exception === 'is_running'"
                class="nodeman-icon nc-icon-audit filtered-icon">
              </i>)
            </span>
            <span class="execut-text" v-else>{{ row.statusDisplay | filterEmpty }}</span>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column
        prop="colspaOpera"
        :width="135 + (fontSize === 'large' ? 20 : 0)"
        :label="$t('操作')"
        :resizable="false">
        <template #default="{ row }">
          <div>
            <bk-button
              v-test="'log'"
              class="mr10"
              text
              v-if="row.status !== 'filtered' && row.status !== 'ignored'"
              theme="primary"
              @click.stop="handleRowView('viewLog', row)">
              {{ $t('查看日志') }}
            </bk-button>
            <loading-icon v-if="row.loading"></loading-icon>
            <template v-else>
              <bk-button
                v-test="'singleRetry'"
                text
                v-if="row.status === 'failed'"
                theme="primary"
                @click="handleRowOperate('retry',[row])">
                {{ $t('重试') }}
              </bk-button>
              <bk-button
                v-test="'singleStop'"
                text
                v-if="row.status === 'running'"
                theme="primary"
                @click="handleRowOperate('stop',[row])">
                {{ $t('终止') }}
              </bk-button>
            </template>
          </div>
        </template>
      </bk-table-column>
    </bk-table>
    <TaskDetailSlider
      :task-id="taskId"
      :slider="slider"
      :table-list="tableList"
      v-model="slider.show">
    </TaskDetailSlider>
  </section>
</template>

<script lang="ts">
import { Component, Prop, Emit, Mixins } from 'vue-property-decorator';
import { MainStore } from '@/store';
import { ITaskHost, IRow } from '@/types/task/task';
import { IPagination, ISearchItem } from '@/types';
import { isEmpty, takesTimeFormat } from '@/common/util';
import TaskDetailSlider from './task-detail-slider.vue';
import HeaderRenderMixin from '@/components/common/header-render-mixins';

@Component({
  name: 'task-detail-table',
  components: {
    TaskDetailSlider,
  },
})
export default class TaskDeatailTable extends Mixins(HeaderRenderMixin) {
  @Prop({ type: [String, Number], default: '' }) private readonly taskId!: string | number;
  @Prop({ type: String, default: '' }) private readonly status!: string;
  @Prop({ type: Object, default: () => ({
    limit: 50,
    current: 1,
    count: 0,
    limitList: [50, 100, 200],
  }),
  }) private readonly pagination!: IPagination;
  @Prop({ type: Array, default: () => ([]) }) private readonly tableList!: Array<ITaskHost>;
  @Prop({ type: Boolean, default: false }) private readonly loading!: boolean;
  @Prop({ type: Array, default: () => ([]) }) public readonly filterData!: ISearchItem[];
  @Prop({ type: Array, default: () => ([]) }) private readonly selected!: Array<IRow>;
  @Prop({ type: String, default: '' }) private readonly jobType!: string;
  @Prop({ type: String, default: '' }) private readonly operateHost!: string;
  @Prop({ type: Boolean, default: false }) private readonly showCommindBtn!: boolean;

  private commandLoading = false;
  private titleStatusMap: Dictionary = {
    running: window.i18n.t('正在执行'),
    failed: window.i18n.t('执行失败'),
    part_failed: window.i18n.t('部分失败'),
    success: window.i18n.t('执行成功'),
    stop: window.i18n.t('已终止'),
    pending: window.i18n.t('等待执行'),
    terminated: window.i18n.t('已终止'),
    filtered: window.i18n.t('已忽略'),
    ignored: window.i18n.t('已忽略'),
  };
  private slider: Dictionary = {
    show: false,
    isSingle: false,
    hostType: '',
    opType: '',
    row: {},
  };

  private get fontSize() {
    return MainStore.fontSize;
  }
  private get tableHeight() {
    return MainStore.windowHeight - 322;
  }
  private get isUninstallType() {
    return /UN/ig.test(this.jobType);
  }
  private get commandStepText() {
    return this.isUninstallType ? this.$t('手动卸载Guide') : this.$t('手动安装Guide');
  }

  @Emit('row-operate')
  public handleRowOperate(type: string, rowList: ITaskHost[]) {
    return { type, selected: rowList };
  }

  @Emit('pagination-change')
  public handlePaginationChange({ type, value }: { type: string, value: string | number }) {
    return { type, value };
  }

  @Emit('select-change')
  public handleSelect(selected: ITaskHost[]) {
    return selected;
  }

  public handleRowView(type: string, row: ITaskHost) {
    if (type === 'viewLog') {
      this.$router.push({
        name: 'taskLog',
        params: {
          taskId: this.taskId as string,
          instanceId: row.instanceId.toString(),
        },
        query: {
          page: String(this.pagination.current),
          pageSize: String(this.pagination.limit),
        },
      });
    } else if (type === 'viewCommind') {
      this.slider.isSingle = true;
      this.slider.row = row;
      this.slider.show = true;
      this.slider.opType = row.opTypeDisplay;
      // if (row) {
      if (this.operateHost === 'Proxy') {
        this.slider.hostType = this.operateHost;
      } else {
        this.slider.hostType = row.bkCloudId === window.PROJECT_CONFIG.DEFAULT_CLOUD ? 'Agent' : 'Pagent';
      }
      // 目前已没有查看所有命令操作
      // } else {
      //   this.slider.hostType = this.operateHost === 'Proxy' ? this.operateHost : 'mixed'
      // }
    } else if (type === 'filterrd') { // 已忽略且正在运行的主机跳转
      if (row.jobId && row.exception && row.exception === 'is_running') {
        this.$router.push({
          name: 'taskLog',
          params: {
            taskId: `${row.jobId}`,
            hostInnerIp: row.innerIp,
          },
          query: {
            page: String(this.pagination.current),
            pageSize: String(this.pagination.limit),
          },
        });
      }
    }
  }
  // 分页
  public pageChange(page: number) {
    this.handlePaginationChange({ type: 'current', value: page || 1 });
  }
  // 分页条数
  public limitChange(limit: number) {
    this.handlePaginationChange({ type: 'limit', value: limit || 1 });
  }
  public filteredTitle(row: ITaskHost) {
    return `${this.titleStatusMap[row.status]} ${(row.statusDisplay || '').replace(/\s+/g, ' ')}`;
  }
  public getSelectAbled(row: ITaskHost) {
    return row.status !== 'filtered' && row.status !== 'pendding';
  }
  public installTypeCell(cell: boolean | undefined) {
    if (isEmpty(cell)) {
      return '--';
    }
    return cell ? this.$t('手动') : this.$t('远程');
  }
  public takesTimeFormat(date: number) {
    return takesTimeFormat(date);
  }
}
</script>

<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  .task-detail-table {
    .execut-text {
      &.has-icon {
        cursor: pointer;
      }
      &:hover .filtered-icon {
        color: #3a84ff;
      }
    }
    .primary,
    .running {
      color: #3a84ff;
    }
    .success {
      color: #2dcb56;
    }
    .warning,
    .filtered，
    .ignored {
      color: #ff9c01;
    }
    .failed,
    .stop {
      color: #ea3636;
    }
    .pending {
      color: #63656e;
    }
    .disabled {
      color: #c4c6cc;
      cursor: not-allowed;
    }
  }
  /deep/ .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  /deep/ .row-ip .cell {
    padding-left: 24px;
  }
</style>
