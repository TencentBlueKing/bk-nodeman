<template>
  <div class="task-detail-wrapper" v-test="'taskDetail'" v-bkloading="{ isLoading: loading }">
    <template v-if="!loading">
      <TaskDetailInfo
        :detail="detail"
        :task-status="taskStatus"
        :manual-waiting="showCommind && hasWaitingHost"
        :operate-host="operateHost">
      </TaskDetailInfo>
      <div
        v-if="taskStatus === 'pending'"
        v-bkloading="{
          isLoading: true,
          title: $t('任务创建中请稍后')
        }"
        style="flex: 1;">
      </div>
      <template v-else>
        <section class="detail-option h32">
          <CopyDropdown
            :list="copyTypeList"
            :disabled="!tableList.length"
            :associate-cloud="false"
            :get-ips="handleCopyIp" />
          <bk-button
            v-test="'stop'"
            class="ml10"
            hover-theme="danger"
            :loading="stopLoading"
            :disabled="staticDetail.running === 0 || stopLoading"
            @click="handleTaskStop([])">
            {{ stopLoading ? '' : $t('终止') }}
          </bk-button>
          <bk-button
            v-test="'retry'"
            class="ml10"
            :loading="retryLoading"
            :disabled="staticDetail.failed === 0 || retryLoading"
            @click.stop="handleTaskRetry([])">
            {{ $t('失败重试')}}
          </bk-button>
          <bk-search-select
            ref="searchSelect"
            v-test="'filter'"
            class="fr task-filter-select"
            split-code=","
            :show-condition="false"
            :placeholder="$t('请输入')"
            :data="searchSelectData"
            v-model="searchSelectValue"
            @paste.native.capture.prevent="handlePaste"
            @change="reGetDetailList">
          </bk-search-select>
        </section>
        <section class="detail-table-content">
          <div class="table-header">
            <div class="table-header-left">
              <span class="package-name">{{ jobTypeDisplay }}</span>
              <i18n path="机器数量" class="package-selection">
                <span class="selection-num">{{ staticDetail.all }}</span>
              </i18n>
            </div>
            <div class="table-header-right">
              <template v-for="(item, index) in treeShakingStatus">
                <span :key="item.status">
                  <span
                    :class="`filter-num ${item.status}`"
                    @click="numFilterHandle(item.status.toLocaleUpperCase())">
                    {{ item.value }}
                  </span>
                  {{ statusMap[item.status] }}
                  <span class="separator" v-if="index !== (treeShakingStatus.length - 1)">,</span>
                  <span
                    class="dot"
                    v-if="item.status === 'running' && index === (treeShakingStatus.length - 1)">
                    ...
                  </span>
                </span>
              </template>
            </div>
          </div>
          <TaskDetailTable
            :task-id="taskId"
            :status="status"
            :loading="tableLoading"
            :filter-data="filterData"
            :search-select-value="searchSelectValue"
            :table-list="tableList"
            :pagination="pagination"
            :category="detail.category"
            :operate-host="operateHost"
            :show-commind-btn="showCommind"
            @row-operate="handleOperate"
            @filter-confirm="handleFilterHeaderChange"
            @filter-reset="handleFilterHeaderChange"
            @pagination-change="handlePaginationChange"
            @empty-clear="emptySearchClear"
            @empty-refresh="getDetailListDebounce">
          </TaskDetailTable>
        </section>
      </template>
    </template>
  </div>
</template>

<script lang="tsx">
import { Component, Prop, Mixins, Ref } from 'vue-property-decorator';
import { AgentStore, TaskStore, MainStore } from '@/store/index';
import TaskDetailTable from './task-detail-table.vue';
import TaskDetailInfo from './task-detail-info.vue';
import HeaderFilterMixins from '@/components/common/header-filter-mixins';
import PollMixin from '@/common/poll-mixin';
import { ICondition, IPagination, ISearchChild, ISearchItem } from '@/types';
import { ITaskHost, ITotalCount, ITask, ITaskParams } from '@/types/task/task';
import { debounce, searchSelectPaste, takesTimeFormat, toHump } from '@/common/util';
import { Route } from 'vue-router';
import CopyDropdown from '@/components/common/copy-dropdown.vue';

Component.registerHooks([
  'beforeRouteLeave',
]);

@Component({
  name: 'task-detail-new',
  components: {
    TaskDetailInfo,
    TaskDetailTable,
    CopyDropdown,
  },
})
export default class TaskDeatail extends Mixins(PollMixin, HeaderFilterMixins) {
  @Prop({ type: [String, Number], default: '', required: true }) private readonly taskId!: string | number;
  @Prop({ type: String, default: '' }) private readonly status!: string;

  @Ref('searchSelect') private readonly searchSelect!: any;

  private loading = false;
  private tableLoading = false;
  private stopLoading = false;
  private retryLoading = false;
  private pollStatus = ['running', 'pending']; // 需要轮询的状态
  private pagination: IPagination = {
    limit: 50,
    current: 1,
    count: 0,
    limitList: [50, 100, 200],
  };
  private tableList: ITaskHost[] = [];
  private staticDetail: { [key: string]: number } = {
    failed: 0,
    filtered: 0,
    ignored: 0,
    success: 0,
    running: 0,
    pending: 0,
    all: 0,
  };
  private loadMessage = true;
  private taskStatus = '';
  private jobType = '';
  private jobTypeDisplay = '';
  private timestamp = '';
  private statusMap = {
    success: window.i18n.t('个成功'),
    failed: window.i18n.t('个失败'),
    filtered: window.i18n.t('个忽略'),
    ignored: window.i18n.t('个忽略'),
    running: window.i18n.t('个执行中'),
    pending: window.i18n.t('个等待执行'),
  };
  private detail: { [key: string]: string } = {};
  public filterData: ISearchItem[] = [
    { name: 'IP', id: 'ip' },
    {
      name: window.i18n.t('执行状态'),
      id: 'status',
      multiable: true,
      children: [
        { id: 'PENDING', name: window.i18n.t('等待执行'), checked: false },
        { id: 'RUNNING', name: window.i18n.t('正在执行'), checked: false },
        { id: 'SUCCESS', name: window.i18n.t('执行成功'), checked: false },
        { id: 'FAILED', name: window.i18n.t('执行失败'), checked: false },
        { id: 'IGNORED', name: window.i18n.t('已忽略'), checked: false },
      ],
    },
  ];
  private copyTypeList = [
    { name: this.$t('所有IP'), id: '' },
    { name: this.$t('被忽略IP'), id: 'ignored' },
    { name: this.$t('失败IP'), id: 'failed' },
    { name: this.$t('成功IP'), id: 'success' },
  ];
  private getDetailListDebounce = function () {};

  // search select数据源
  private get searchSelectData() {
    const ids = this.searchSelectValue.map((item: ISearchItem) => item.id);
    return this.filterData.filter(item => !ids.includes(item.id));
  }
  // 获取个数非零的状态
  private get treeShakingStatus() {
    return Object.keys(this.staticDetail).filter(key => key !== 'all' && !!this.staticDetail[key])
      .map(key => ({
        status: key,
        value: this.staticDetail[key],
      }));
  }
  // 是否为手动类型安装机器
  private get isManualType() {
    return this.tableList.some((row: ITaskHost) => row.isManual);
  }
  // 操作的主机或任务类型 Agent | Proxy | Plugin
  private get operateHost() {
    const res = /(agent)|(proxy)|(plugin)/ig.exec(this.jobType);
    return res ? res[0] : '';
  }
  // 能查看命令的任务类型
  private get showCommind() {
    if (this.operateHost && this.isManualType) {
      return /INSTALL/ig.test(this.jobType);
    }
    return false;
  }
  private get manualStepText(): string[] {
    return /UN/ig.test(this.jobType) ? [window.i18n.t('手动卸载Guide'), '卸载'] : [window.i18n.t('手动安装Guide'), '安装'];
  }
  private get hasWaitingHost() {
    return this.tableList.some(item => this.manualStepText.includes(item.step as string) && item.status === 'running');
  }

  private created() {
    this.getDetailListDebounce = debounce(300, this.getTaskDetail);
    this.loading = true;
    MainStore.updateRouterBackName(this.$route.params.routerBackName || '');
    if (this.status) {
      // 会自动触发watch进行搜索
      this.numFilterHandle(this.status);
    } else {
      this.getTaskDetail();
    }
  }

  // 进入详情页才缓存界面
  private beforeRouteLeave(to: Route, from: Route, next: () => void) {
    if (to.name !== 'taskList') {
      MainStore.deleteCachedViewsByName('taskList');
    }
    next();
  }

  public reGetDetailList() {
    this.pagination.current = 1;
    this.getDetailListDebounce();
  }
  public async getTaskDetail() {
    this.tableLoading = true;
    const res = await TaskStore.requestHistoryTaskDetail({
      jobId: this.taskId as number,
      params: this.getParams(),
    });
    if (res) {
      const {
        list, statistics, status, jobType, jobTypeDisplay, total,
        ipFilterList, createdBy, jobId, meta = {}, startTime, costTime,
      } = res as ITask;
      list.forEach((item: ITaskHost) => {
        item.loading = false;
      });
      this.taskStatus = status ? status.toLowerCase() : '';
      this.runingQueue = this.pollStatus.includes(this.taskStatus) ? [1] : [];
      Object.assign(this.detail, {
        jobType: toHump((jobType || '').toLowerCase()),
        jobTypeDisplay: jobTypeDisplay || '--',
        timestamp: this.$filters('filterTimezone', startTime),
        createdBy,
        jobId,
        costTime: takesTimeFormat(costTime),
        category: '',
        ...meta,
      });
      this.jobType = toHump((jobType || '').toLowerCase());
      this.jobTypeDisplay = jobTypeDisplay || '--';
      this.timestamp = startTime || '';
      this.tableList.splice(0, this.tableList.length, ...list);
      this.pagination.count = total || 0;
      this.handleStatistics(statistics, ipFilterList);
    } else {
      this.runingQueue = [];
    }
    if (this.isManualType) {
      AgentStore.getCloudList(); // ...mapActions('agent', ['getCloudList']),
    }
    this.tableLoading = false;
    this.loading = false;
  }
  public handleStatistics(statistics?: ITotalCount, ipFilterList?: string[]) {
    if (statistics) {
      const {
        successCount, failedCount, filterCount, ignoredCount,
        runningCount, pendingCount, totalCount } = statistics;
      Object.assign(this.staticDetail, {
        failed: failedCount || 0,
        filtered: filterCount || 0,
        ignored: ignoredCount || 0,
        success: successCount || 0,
        running: runningCount || 0,
        pending: pendingCount || 0,
        all: totalCount || 0,
      });
      if (this.loadMessage) {
        if (filterCount && ipFilterList && ipFilterList.length) {
          this.$bkMessage({
            theme: 'warning',
            offsetY: 53,
            ellipsisLine: 2,
            message: this.$t('已忽略信息提示', { num: filterCount, ip: ipFilterList[0] }),
          });
        }
        this.loadMessage = false;
      }
    }
  }
  /**
   * 处理轮询的数据
   */
  public async handlePollData() {
    const res = await TaskStore.requestHistoryTaskDetail({
      jobId: this.taskId as number,
      params: this.getParams(),
    });
    if (res) {
      const { list, statistics, status, jobType, jobTypeDisplay, total, costTime } = res;
      Object.assign(this.detail, {
        jobType: toHump((jobType || '').toLowerCase()),
        jobTypeDisplay: jobTypeDisplay || '--',
        costTime: takesTimeFormat(costTime),
      });
      this.taskStatus = status ? status.toLowerCase() : '';
      this.runingQueue = this.pollStatus.includes(this.taskStatus) ? [1] : [];
      this.jobType = toHump((jobType || '').toLowerCase());
      this.jobTypeDisplay = jobTypeDisplay || '--';
      this.pagination.count = total || 0;
      // 带筛选的条件会导致列表为空
      list.forEach((item: ITaskHost) => {
        const current = this.tableList.find((row: ITaskHost) => row.instanceId === item.instanceId);
        item.loading = current ? current.loading : false;
      });
      this.tableList.splice(0, this.tableList.length, ...list);
      this.handleStatistics(statistics);
    } else {
      this.runingQueue = [];
    }
    return res;
  }
  public getParams() {
    const params: ITaskParams = {
      page: this.pagination.current,
      pagesize: this.pagination.limit,
    };
    const conditions: ICondition[] = [];
    const searchObj: {
      [key: string]: Array<string>
    } = this.searchSelectValue.reduce((obj: Dictionary, item: ISearchItem) => {
      if (item.values) {
        const valueArr = item.values.map((value: ISearchChild) => value.id);
        if (Object.prototype.hasOwnProperty.call(obj, item.id)) {
          obj[item.id] = obj[item.id].concat(valueArr);
        } else {
          obj[item.id] = valueArr;
        }
      } else {
        obj[item.id] = [item.name];
      }
      return obj;
    }, {});
    const keys = ['ip', 'status'];
    // 多IP搜索传参
    Object.entries(searchObj).forEach((item: any[]) => {
      const [key, val] = item;
      const value: string[] = Array.from(val);
      if (keys.includes(key)) {
        conditions.push({ key, value });
      } else {
        conditions.push({ key: 'ip', value });
      }
    });
    if (conditions.length) {
      params.conditions = conditions;
    }
    return params;
  }
  public numFilterHandle(status: string) {
    if (!status) return;
    const item = this.filterData[1].children
      ? this.filterData[1].children.find((item: ISearchChild) => item.id === status) : {};
    this.filterData.forEach((data) => {
      if (data.id === 'status' && data.children) {
        data.children = data.children.map((child) => {
          child.checked = child.id === status;
          return child;
        });
      }
    });
    this.searchSelectValue.splice(0, this.searchSelectValue.length);
    this.handlePushValue('status', [item as ISearchChild], false);
    this.reGetDetailList();
  }
  // 搜索框: search-select change
  public handleSearchChange(list: ISearchItem[]) {
    this.filterData.forEach((data: ISearchItem) => {
      const children = list.find(item => item.id === data.id);
      if (data.children) {
        data.children = data.children.map((child: ISearchChild) => {
          if (!children) {
            child.checked = false;
          } else {
            child.checked = children.values ? children.values.some(value => value.id === child.id) : false;
          }
          return child;
        });
      }
    });
    this.searchSelectValue = list;
    this.reGetDetailList();
  }
  // 表头筛选: table-head-filter change
  public handleFilterHeaderChange(param: { prop: string, list?: ISearchChild[] }) {
    if (param.list) {
      this.tableHeaderConfirm(param as { prop: string, list: ISearchChild[] });
    } else {
      this.tableHeaderReset(param);
    }
    this.reGetDetailList();
  }
  // 分页: page、limit change
  public handlePaginationChange({ type, value }: { type: 'limit' | 'current', value: number }) {
    this.pagination[type] = value;
    if (type === 'limit') {
      this.reGetDetailList();
    } else {
      this.getDetailListDebounce();
    }
  }
  public handleOperate({ type, selected }: { type: string, selected: ITaskHost[] }) {
    if (type === 'retry') {
      this.handleTaskRetry(selected);
    } else {
      this.handleTaskStop(selected);
    }
  }
  public async handleTaskStop(seleced: ITaskHost[]) {
    const isBatch = !seleced.length;
    if (!isBatch && seleced.find(item => item.loading)) {
      return false;
    }
    this.stopLoading = true;
    const data = isBatch ? [] : seleced;
    this.setRowsLoading(data, true);
    const res = await TaskStore.requestTaskStop({
      jobId: this.taskId as number,
      params: { instance_id_list: data.map(item => item.instanceId) } as any,
    });
    if (res.result) {
      this.staticDetail.failed += data.length;
      this.staticDetail.running -= data.length;
      this.handleStatistics();
      this.setRowsStatus(data, 'failed');
    }
    this.stopLoading = false;
    this.setRowsLoading(data, false);
    // 带筛选条件时需要重新加载列表
    if (res.result) {
      await this.handlePollData();
    }
  }
  public async handleTaskRetry(seleced: ITaskHost[]) {
    const isBatch = !seleced.length;
    const data = isBatch ? [] : seleced;
    if (!isBatch && seleced.find(item => item.loading)) {
      return false;
    }
    this.retryLoading = true;
    this.setRowsLoading(data, true);
    const res = await TaskStore.requestTaskRetry({
      jobId: this.taskId as number,
      params: { instance_id_list: data.map(item => item.instanceId) } as any,
    });
    this.retryLoading = false;
    if (res.result) {
      this.taskStatus = 'running';
      this.runingQueue = [1];
      this.setRowsStatus(data, 'pending');
      this.staticDetail.failed -= data.length;
      this.staticDetail.pending += data.length;
      this.handleStatistics();
    }
    this.setRowsLoading(data, false);
    // 带筛选条件时需要重新加载列表
    if (res.result) {
      await this.handlePollData();
    }
  }
  public setRowsStatus(data: ITaskHost[], status: string) {
    data.forEach((row) => {
      if (status === 'pending' && row.status === 'failed') {
        row.status = status;
        row.statusDisplay = window.i18n.t('等待执行');
      } else if (status === 'failed' && this.pollStatus.includes(row.status)) {
        row.status = status;
        row.statusDisplay = window.i18n.t('已终止');
      }
    });
  }
  public setRowsLoading(data: ITaskHost[], isLoading: boolean) {
    data.forEach((row) => {
      row.loading = isLoading;
    });
  }
  public async handleCopyIp(type: string) {
    const ipKey = this.$DHCP && type.includes('v6') ? 'innerIpv6' : 'innerIp';
    // const associateCloud = type.includes('cloud');
    const params: ITaskParams = {
      pagesize: -1,
    };
    const status = type.split('_')?.[0];
    // if (associateCloud) {
    //   params.cloud_id_ip = {
    //     [ipKey.includes('v6') ? 'ipv6' : 'ipv4']: true,
    //   };
    // }
    if (status) {
      params.conditions = [
        { key: 'status', value: [status.toUpperCase()] },
      ];
    }
    const res = await TaskStore.requestHistoryTaskDetail({ jobId: this.taskId as number, params });
    if (res) {
      return Promise.resolve(res.list.map((item: {
        innerIpv6: string
        innerIp: string
      }) => item[ipKey]).filter((item: string) => !!item));
    }
    return Promise.resolve([]);
  }

  public handlePaste(e: any): void {
    searchSelectPaste({
      e,
      selectedValue: this.searchSelectValue,
      filterData: this.filterData,
      selectRef: this.searchSelect,
      pushFn: this.handlePushValue,
      changeFn: this.reGetDetailList,
    });
  }
  public emptySearchClear() {
    this.tableLoading = true;
    this.handleSearchChange([]);
  }
}
</script>

<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";
  @import "@/css/variable.css";
  @import "@/css/transition.css";
  $headerColor: #313238;

  >>> .icon-down-wrapper {
    position: relative;
    left: 3px;
  }
  .task-detail-wrapper {
    display: flex;
    flex-direction: column;
    padding: 0 0 30px 0;
    background: #fff;
    overflow: hidden;
    .detail-option {
      padding: 0 24px;
      margin: 24px 0 0 0;
      .copy-dropdown-btn {
        font-size: 14px;
      }
      >>> .bk-button-loading {
        /* stylelint-disable-next-line declaration-no-important */
        background-color: unset !important;
        * {
          /* stylelint-disable-next-line declaration-no-important */
          background-color: #63656e !important;
        }
      }
    }
    .detail-table-content {
      margin-top: 14px;
      padding: 0 24px;
      .table-header {
        padding: 0 24px;
        margin-bottom: -1px;
        height: 42px;
        background: #f0f1f5;
        border: 1px solid #dcdee5;
        border-radius: 2px 2px 0 0;

        @mixin layout-flex row, center, space-between;
        &-left {
          font-weight: Bold;
          .package-selection {
            color: #979ba5;
          }
        }
        &-right {
          .filter-num {
            font-weight: bold;
            cursor: pointer;
          }
        }
      }
    }
    .task-filter-select {
      width: 500px;
      background: #fff;
    }
    .primary,
    .running {
      color: $primaryFontColor;
    }
    .success {
      color: $bgSuccess;
    }
    .warning,
    .filtered,
    .ignored {
      color: $bgWarning;
    }
    .failed,
    .stop {
      color: $bgFailed;
    }
    .pending {
      color: $defaultFontColor;
    }
    .disabled {
      color: #c4c6cc;
      cursor: not-allowed;
    }
  }
</style>
