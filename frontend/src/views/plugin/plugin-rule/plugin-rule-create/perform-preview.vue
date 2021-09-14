<template>
  <div v-test.policy="'preview'" class="perform-preview" v-bkloading="{ isLoading: loading || stepLoading }">
    <div class="tc" v-if="invisibleStep > -1">
      <ExceptionCard type="dataAbnormal" :text="$t('仍有步骤未完成，无法预览')" :has-border="false">
        <bk-button
          slot="content"
          class="completion-btn"
          theme="primary"
          v-test.policy="'stepBtn'"
          @click="handleStepChange(invisibleStep)">
          {{ '跳转处理' }}
        </bk-button>
      </ExceptionCard>
    </div>
    <template v-else>
      <template v-if="showTips">
        <Tips class="mb15" v-if="isGrayTips" theme="warning">
          <i18n v-if="isDeleteGrayType" path="执行删除操作后灰度策略关联的所有将回滚至主策略版本">
            {{ pluginName }}
            <b>{{ $t('回滚') }}</b>
          </i18n>
          <i18n v-else path="执行发布操作后主策略关联的所有将调整为当前灰度版本">
            <b>{{ $t('主策略') }}</b>
            {{ pluginName }}
          </i18n>
        </Tips>
        <Tips class="mb15" v-else :theme="tipsTheme">
          <template #default>
            <div>
              {{ tipsContext }}
              <bk-popconfirm
                v-if="showDeleteBtn && !deleteLoading"
                trigger="click"
                width="280"
                @confirm="deletePolicy()">
                <template slot="content">
                  <div class="title">{{ $t('是否强制删除此策略') }}</div>
                  <i18n path="当前策略下仍关联主机">
                    <span class="primary">{{ totalNum }}</span>
                  </i18n>
                </template>
                <span class="primary btn ml30">{{ $t('强制删除') }}</span>
              </bk-popconfirm>
            </div>
          </template>
        </Tips>
      </template>
      <div class="table-status">
        <div class="tab-wrapper">
          <bk-tab
            ref="previewTabRef"
            ext-cls="preview-tab"
            type="card"
            :label-height="42"
            :active="tabActive"
            @tab-change="handleTabChange">
            <bk-tab-panel
              v-for="(panel, index) in targetTabList"
              v-test.policy="'tableTab'"
              v-bind="panel"
              :key="`${index}_${panel.total}`">
              <template slot="label">
                <div v-if="panel.name !== 'loading'" style="visibility: hidden;">
                  <span class="panel-name">{{ panel.label }}</span>
                  <span class="panel-total" v-if="panel.name !== 'all'">{{ panel.total }}</span>
                </div>
                <div :class="['panel-content', { 'panel-error-content': panel.name === 'MAIN_STOP_PLUGIN' }]">
                  <bk-button theme="default" v-if="panel.name === 'loading'" :loading="true" />
                  <div v-else>
                    <span class="panel-name">{{ panel.label }}</span>
                    <span class="panel-total" v-if="panel.name !== 'all'">{{ panel.total }}</span>
                  </div>
                </div>
              </template>
            </bk-tab-panel>
          </bk-tab>
        </div>
        <div class="filter-content" v-if="totalNum && isAllTab">
          <template v-for="(item, index) in statisticsList">
            <i18n :path="item.path" :key="index">
              <span :class="['filter-num', item.id]"
                    @click="numFilterHandle(item.id.toUpperCase())">
                {{ item.count }}
              </span>
            </i18n>
            <span v-if="index < (statisticsList.length - 1)" class="mr5" :key="`separator-${index}`">,</span>
          </template>
        </div>
      </div>
      <bk-table
        ref="previewTableRef"
        v-test.policy="'previewTable'"
        :data="data"
        :pagination="pagination"
        :max-height="windowHeight - calcHeight"
        @sort-change="handleSortChange"
        @page-change="handlePageChange"
        @page-limit-change="handlePageLimitChange">
        <bk-table-column :label="$t('主机IP')" prop="inner_ip" />
        <bk-table-column :label="$t('云区域')" prop="bk_cloud_id" :render-header="renderFilterHeader">
          <template #default="{ row }">{{ row.bk_cloud_name }}</template>
        </bk-table-column>
        <!-- 忽略的没有这两列信息 -->
        <template v-if="!isIgnoredTab || !isManualType">
          <bk-table-column :label="$t('所属业务')" prop="bk_biz_name" :render-header="renderFilterHeader">
            <template #default="{ row }">{{ row.bk_biz_name | filterEmpty }}</template>
          </bk-table-column>
          <bk-table-column :label="$t('操作系统')" prop="os_type" :render-header="renderFilterHeader">
            <template #default="{ row }">{{ row.os_type | filterEmpty }}</template>
          </bk-table-column>
        </template>
        <bk-table-column
          v-if="isAllTab || isRollbackTab"
          prop="status"
          :label="$t('Agent状态')"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            <div class="col-status">
              <span :class="'status-mark status-' + row.status"></span>
              <span>{{ row.statusDisplay || $t('未知') }}</span>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          v-if="isIgnoredTab && !isManualType"
          :label="$t('忽略原因')"
          prop="msg"
          key="msg"
          show-overflow-tooltip
          min-width="400"
        />
        <bk-table-column
          v-else-if="isIgnoredTab && isManualType"
          :label="$t('部署策略')"
          show-overflow-tooltip
          key="suppressed_by_name"
          min-width="200">
          <template #default="{ row }">
            <router-link
              class="bk-primary bk-button-normal bk-button-text policy-link-btn"
              tag="a"
              target="_blank"
              :to="{
                path: '/plugin-manager/rule',
                query: { name: row.suppressed_by_name }
              }">
              {{ row.suppressed_by_name }}
              <i class="nodeman-icon nc-jump-link"></i>
            </router-link>
          </template>
        </bk-table-column>
        <bk-table-column
          v-else-if="isRollbackTab"
          :label="$t('目标策略')"
          show-overflow-tooltip
          key="target_policy"
          min-width="200">
          <template #default="{ row }">
            <router-link
              v-if="row.target_policy.id"
              class="bk-primary bk-button-normal bk-button-text policy-link-btn"
              tag="a"
              target="_blank"
              :to="{
                path: '/plugin-manager/rule',
                query: { name: row.target_policy.name }
              }">
              {{ row.target_policy.name }}
              <i class="nodeman-icon nc-jump-link"></i>
            </router-link>
            <span v-else>{{ row.target_policy.msg | filterEmpty }}</span>
          </template>
        </bk-table-column>
        <template v-else-if="!hideVersionColumn">
          <bk-table-column :key="tabActive" :label="$t('当前版本')" prop="current_version">
            <template #default="{ row }">{{ row.current_version | filterEmpty }}</template>
          </bk-table-column>
          <bk-table-column :label="$t('目标版本')" prop="target_version">
            <template #default="{ row }">{{ row.target_version | filterEmpty }}</template>
          </bk-table-column>
        </template>
      </bk-table>

      <div class="footer mt30">
        <bk-popover placement="top" :disabled="!noHostAvailable">
          <bk-button
            v-test.common="'formCommit'"
            theme="primary"
            class="nodeman-primary-btn"
            :loading="executeLoading"
            :disabled="executeBtnDisabled"
            @click="handleExec">
            {{ $t('立即执行') }}
          </bk-button>
          <template #content>{{ $t('当前没有可操作的主机') }}</template>
        </bk-popover>
        <template v-if="showDeleteBtn">
          <bk-button v-if="deleteLoading" v-test.policy="'deleteBtn'" disabled>{{ $t('强制删除') }}</bk-button>
          <bk-popconfirm
            v-else
            trigger="click"
            width="280"
            class="ml5"
            @confirm="deletePolicy()">
            <template slot="content">
              <div class="title">{{ $t('是否强制删除此策略') }}</div>
              <i18n path="当前策略下仍关联主机">
                <span class="primary">{{ totalNum }}</span>
              </i18n>
            </template>
            <bk-button v-test.policy="'deletePopBtn'">{{ $t('强制删除') }}</bk-button>
          </bk-popconfirm>
        </template>
        <bk-button
          v-if="hasPreStep"
          v-test.common="'stepPrev'"
          class="nodeman-cancel-btn ml5"
          @click="handleStepChange(step - 1)">
          {{ $t('上一步') }}
        </bk-button>
        <bk-button
          class="nodeman-cancel-btn ml5"
          @click="handleCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </template>
  </div>
</template>
<script lang="ts">
import { Component, Emit, Prop, Mixins, Ref } from 'vue-property-decorator';
import { MainStore, PluginStore } from '@/store';
import { IAgentStatus, IPagination, ISearchChild, ISearchItem, ISortData } from '@/types';
import { IPolicyOperate, IPreviewHost } from '@/types/plugin/plugin-type';
import HeaderRenderMixin from '@/components/common/header-render-mixins';
import HeaderFilterMixins from '@/components/common/header-filter-mixins';
import Tips from '@/components/common/tips.vue';
import ExceptionCard from '@/components/exception/exception-card.vue';
import {
  pluginOperate, previewOperate, manualNotSteps, policyUpdateType, policyOperateType, notCalculate,
} from '@/views/plugin/operateConfig';

/**
 * 包含的所有类型：
 * 插件 所有操作
 * 主策略 创建、更新、启用、停用、强制删除(stop_and_delete)
 * 灰度策略 创建、更新、发布、删除
 */

type OperateType = 'start' | 'stop' | 'stop_and_delete'; // 策略状态操作类型
type ManualType = 'MAIN_INSTALL_PLUGIN'; // 手动操作插件类型
interface tabItem {
  name: string
  label: string
  total?: number
  disabled?: boolean
  data?: IPreviewHost[]
}

@Component({
  name: 'perform-preview',
  components: { Tips, ExceptionCard },
})
export default class PerformPreview extends Mixins(HeaderRenderMixin, HeaderFilterMixins) {
  @Prop({ default: 'create', type: String }) private readonly type!: string;
  @Prop({ default: '', type: [String, Number] }) private readonly ruleId!: string | number;
  @Prop({ default: () => [], type: Array }) private readonly abnormalHost!: number[];
  @Prop({ default: '', type: String })private readonly pluginName!: string;
  @Prop({ default: true, type: Boolean }) private readonly hasPreStep!: boolean;
  @Prop({ default: true, type: Boolean }) private readonly stepLoading!: boolean;
  @Prop({ type: Number, default: 4 }) private readonly step!: number;
  @Prop({ type: Number, default: -1 }) private readonly invisibleStep!: number;

  @Ref('previewTableRef') private readonly previewTableRef: any;
  @Ref('previewTabRef') private readonly previewTabRef: any;

  private loading = false;
  private migrateLoading = false;
  private executeLoading = false;
  private deleteLoading = false;
  private tabActive = 'all';
  // 手动安装/更新插件不需要 策略部署范围tab(全部)
  private targetTabList: tabItem[] = [];
  private data: IPreviewHost[] = [];
  private totalNum = 0;
  private runningNum = 0;
  private terminatedNum = 0;
  private notInstalledNum = 0;
  private pagination: IPagination = {
    limit: 50,
    current: 1,
    count: 0,
    limitList: [50, 100, 200],
  };
  private sortData: ISortData = {
    head: '',
    sort_type: '',
  };
  private osMap: Dictionary = {
    LINUX: 'Linux',
    WINDOWS: 'Windows',
    AIX: 'AIX',
  };
  private statusMap = {
    running: window.i18n.t('正常'),
    terminated: window.i18n.t('异常'),
    not_installed: window.i18n.t('未安装'),
  };
  public filterData: ISearchItem[] = [];


  private get statisticsList() {
    return [
      { id: 'running', count: this.runningNum, path: '正常agent个数' },
      { id: 'terminated', count: this.terminatedNum, path: '异常agent个数' },
      { id: 'not_installed', count: this.notInstalledNum, path: '未安装agent个数' },
    ].filter(item => !!item.count);
  }

  private get jobType() {
    return this.type.replace(/gray/ig, '');
  }
  private get isAllTab() {
    return this.tabActive === 'all';
  }
  private get isRollbackTab() {
    return this.tabActive === 'rollback';
  }
  /** 仅 table cell 展示使用 */
  private get isInstallTab() { // 包含安装类型 需要展示当前版本和目标版本
    return ['INSTALL', 'MAIN_INSTALL_PLUGIN'].includes(this.tabActive);
  }
  private get isIgnoredTab() { // 忽略类型 需要展示忽略原因 或 策略跳转
    return 'IGNORED' === this.tabActive;
  }
  private get noHostAvailable() {
    return this.targetTabList.length === 1 && this.targetTabList.find(item => item.name === 'IGNORED');
  }
  private get isGrayRule() {
    return PluginStore.isGrayRule;
  }
  private get isRuleCreateType() {
    return ['create'].includes(this.jobType);
  }
  // 是否为手动操作插件类型
  private get isManualType() {
    return pluginOperate.includes(this.jobType);
  }
  // 仅需要预览的操作类型
  private get isPreviewType() {
    return previewOperate.includes(this.jobType);
  }
  // 策略更新类型
  private get isPolicyUpdateType() {
    return policyUpdateType.includes(this.jobType);
  }
  // 策略操作类型
  private get isPolicyOperateType() {
    return policyOperateType.includes(this.jobType);
  }
  // 仅 策略操作类型 用到 ------------
  private get isStopAndDeleteType() {
    return this.jobType === 'stop_and_delete';
  }
  private get hasNormalAgent() {
    return this.totalNum && this.runningNum;
  }
  private get showDeleteBtn() {
    return this.isStopAndDeleteType && this.totalNum && !this.runningNum;
  }
  private get executeBtnDisabled() {
    return this.migrateLoading || (this.isStopAndDeleteType && !this.hasNormalAgent) || this.noHostAvailable;
  }
  // ------------
  // 不需要调用前置计算的操作类型
  private get isNotCalculateType() {
    return notCalculate.includes(this.jobType) || this.isDeleteGrayType;
  }
  // 失败重试类型(比较特殊) 接口 & 参数类似 isNotCalculateType
  private get isRetryAbnormal() {
    return this.jobType === 'RETRY_ABNORMAL';
  }
  private get isDeleteGrayType() {
    return this.type === 'deleteGray';
  }
  // 不需要 全部 - tab 的类型
  private get isNotAllTabItem() {
    return this.isManualType || this.isDeleteGrayType;
  }
  // 展示回滚tips - 缺tab条件判断
  private get showRollbackTips() {
    return this.isDeleteGrayType;
  }
  private get hideVersionColumn() {
    return this.tabActive === 'abnormalHost' || this.isRetryAbnormal;
  }
  private get isGrayTips() {
    return ['deleteGray', 'releaseGray'].includes(this.type);
  }
  private get showTips() {
    return this.showRollbackTips || this.isStopAndDeleteType
      || (this.isManualType && this.targetTabList.find(item => item.name === 'IGNORED'))
      || this.isGrayTips;
  }
  private get tipsTheme() {
    if (this.isStopAndDeleteType) {
      return this.showDeleteBtn ? 'danger' : '';
    }
    return 'warning';
  }
  private get allTabText() {
    return this.isRetryAbnormal ? window.i18n.t('失败重试') : window.i18n.t('策略部署范围');
  }
  private get tipsContext() {
    if (this.isStopAndDeleteType) {
      return this.showDeleteBtn
        ? this.$t('目前待卸载的主机全部异常', [this.totalNum]) : this.$t('当前部署策略下仍有关联的主机策略将在卸载任务执行成功后删除');
    }
    return this.$t('部分目标机器已被部署策略管控无法进行操作如需操作请调整对应的部署策略');
  }
  private get windowHeight() {
    return MainStore.windowHeight;
  }
  private get calcHeight() {
    // nav & title-112, step-42, (contentPadding-50 || contentPadding-40 & tips-47), footer-62
    if (this.isPreviewType) { // 无step
      return this.showTips ? 300 : 260;
    }
    return this.showTips ? 350 : 300;
  }

  @Emit('step-change')
  public handleStepChange(step: number) {
    return step;
  }
  @Emit('cancel')
  public handleCancel() {}
  @Emit('update-loaded')
  public handleUpdateStepLoaded({ step, loaded }: { step: number, loaded?: boolean }) {
    return { step, loaded };
  }

  public created() {
    if (this.isNotCalculateType) {
      if (this.isDeleteGrayType) {
        this.tabActive = 'rollback';
      } else {
        // 删除前置计算tab的loading
        this.targetTabList.splice(1, 1);
      }
    }
    if (this.isNotAllTabItem) {
      // 删除全部tab
      this.targetTabList.splice(0, 1);
    }
    if (this.step === 1) {
      this.initStep();
    }
  }

  private async initStep() {
    if (this.invisibleStep === -1) {
      this.getFilterData();
      this.totalNum = 0;
      this.runningNum = 0;
      this.terminatedNum = 0;
      this.notInstalledNum = 0;
      this.initTabList();
      if (!this.isNotAllTabItem) {
        await this.handleGetTableData();
      } else if (this.isDeleteGrayType) {
        this.loading = true;
        await this.getGrayRulePreviews();
        this.loading = false;
      }
      if (!this.isNotCalculateType) {
        await this.getMigratePreviews();
      }
      this.handleUpdateStepLoaded({ step: this.step, loaded: true });
    }
  }
  private initTabList() {
    const tabList: tabItem[] = [];
    if (this.isDeleteGrayType || !this.isNotCalculateType) {
      tabList.push({ name: 'loading', label: '', disabled: true, total: 0, data: [] });
    }
    if (!this.isNotAllTabItem) {
      tabList.unshift({ name: 'all', label: this.allTabText });
    }
    this.targetTabList.splice(0, this.targetTabList.length, ...tabList);
  }

  private async handleGetTableData() {
    this.loading = true;
    await this.getPreviewData();
    this.loading = false;
  }

  private handleTabChange(name: string) {
    if (name !== 'loading') {
      this.tabActive = name;
      this.handleSearchSelectChange([]);
      this.searchSelectValue = [];
      this.pagination.current = 1;
      this.handleGetTableData();
    }
  }

  private handleSortChange({ prop, order }: Dictionary) {
    Object.assign(this.sortData, {
      head: prop,
      sort_type: order === 'ascending' ? 'ASC' : 'DEC',
    });
    this.handleGetTableData();
  }
  private handlePageChange(page: number) {
    this.pagination.current = page;
    this.handleGetTableData();
  }

  private handlePageLimitChange(limit: number) {
    this.pagination.limit = limit;
    this.handleGetTableData();
  }
  public numFilterHandle(status: string) {
    if (!status) return;
    const item = this.filterData[1].children
      ? this.filterData[1].children.find(item => item.id === status) : {};
    this.filterData.forEach((data) => {
      if (data.id === 'status' && data.children) {
        data.children = data.children.map((child) => {
          child.checked = child.id === status;
          return child;
        });
      }
    });
    this.handlePushValue('status', [item as ISearchChild], false);
    this.handleGetTableData();
  }
  public handleFilterChange(param: { prop: string, list?: ISearchChild[] }) {
    if (param.list) {
      this.tableHeaderConfirm(param as { prop: string, list: ISearchChild[] });
    } else {
      this.tableHeaderReset(param);
    }
    this.handleGetTableData();
  }
  public async getFilterData() {
    if (!this.filterData.length) {
      this.filterData = await PluginStore.getFilterList({ category: 'host' });
    }
  }

  // 预览 - 加载table
  public async getPreviewData() {
    // 全部tab & 灰度删除相关 走接口加载，其它tab走前端搜素
    if (this.isAllTab) {
      const { current, limit } = this.pagination;
      const params: Dictionary = {
        page: current,
        pagesize: limit,
        conditions: this.getConditions(),
      };
      // STOP_AND_DELETE && STOP 的预览主机接口用的是【节点列表】的接口：api/plugin/search/去拉主机列表
      if (this.isNotCalculateType) {
        params.with_agent_status_counter = true;
        if (this.isRetryAbnormal) {
          params.bk_host_id = this.abnormalHost;
        } else {
          params.conditions.push({ key: 'source_id', value: [this.ruleId] });
        }
      } else {
        Object.assign(params, { ...this.getParams() });
      }
      if (this.sortData.head && this.sortData.sort_type) {
        params.sort = Object.assign({}, this.sortData);
      }
      this.loading = true;
      const res = this.isNotCalculateType
        ? await PluginStore.getHostList(params)
        : await PluginStore.getTargetPreview(params);
      this.formatTableDataResult(res, params);
      return Promise.resolve(this.data);
    }
    if (this.isDeleteGrayType) {
      const res = this.isRollbackTab ? await this.getRollbackPreview() : await this.getAgentAbnormalHost();
      this.formatTableDataResult(res, res.params);
      return Promise.resolve(this.data);
    }
    this.frontFilterTableData();
    return Promise.resolve(this.data);
  }

  public formatTableDataResult(res: {
    total: number
    list: IPreviewHost[]
    'agent_status_count': { [key: string]: number }
  }, params: Dictionary) {
    const { agent_status_count: agentStatusCount = {}, total, list } = res;
    const { RUNNING, TERMINATED, NOT_INSTALLED: notInstalled, total: totalNum } = agentStatusCount;
    list.forEach((item) => {
      if (['stop_and_delete', 'stop'].includes(this.jobType)) {
        item.target_version = item.version;
      }
      item.os_type = this.osMap[item.os_type];
      item.status = item.status.toLocaleLowerCase();
      item.statusDisplay = this.statusMap[item.status as IAgentStatus];
      // 业务转化
    });
    const { conditions = [] } = params;
    let resetNum = true;
    if (conditions.length) {
      resetNum = conditions.length === 1 && !!conditions.find((item: Dictionary) => item.key === 'source_id');
    }
    if (resetNum && !this.isRuleCreateType) {
      this.totalNum = totalNum;
      this.totalNum = totalNum;
      this.runningNum = RUNNING;
      this.terminatedNum = TERMINATED;
      this.notInstalledNum = notInstalled;
    }
    this.data = list;
    this.pagination.count = total;
  }

  // 计算前置变更 - 全部数据，需前端分页
  public async getMigratePreviews() {
    this.migrateLoading = true;
    const { current, limit } = this.pagination;
    const params: Dictionary = {
      page: current,
      pagesize: limit,
      conditions: this.getConditions(),
      ...this.getParams(),
    };
    if (this.jobType !== 'create') {
      params.policy_id = this.ruleId;
    }
    if (this.sortData.head && this.sortData.sort_type) {
      params.sort = Object.assign({}, this.sortData);
    }
    if (this.jobType === 'start') {
      params.job_type = 'MAIN_START_PLUGIN';
    }
    // 手动操作插件属于一次性订阅
    if (this.isManualType) {
      params.category = 'once';
      params.plugin_name = PluginStore.strategyData.plugin_info?.name;
      params.job_type = this.jobType;
    }
    const res = await PluginStore.getMigratePreview(params);
    this.migrateLoading = false;
    const startIndex = this.isNotAllTabItem ? 0 : 1;
    const length = this.isNotAllTabItem ? this.targetTabList.length : this.targetTabList.length - 1;
    this.targetTabList.splice(startIndex, length, ...res.map(item => ({
      name: item.action_id,
      label: item.action_name,
      total: item.list.length,
      data: item.list.map((row: Dictionary) => ({
        ...row,
        inner_ip: row.ip,
        os_type: this.osMap[row.os_type] || row.os_type || '--',
        current_version: row.migrate_reason ? row.migrate_reason.current_version || '--' : '--',
        target_version: row.migrate_reason ? row.migrate_reason.target_version || '--' : '--',
      })),
    })));
    return Promise.resolve(this.targetTabList);
  }

  // 灰度策略 - 预览加载: 回滚tab & agent异常tab
  public async getGrayRulePreviews() {
    return Promise.all([this.getRollbackPreview(), this.getAgentAbnormalHost()]).then(([res1, res2]) => {
      const { total, params } = res1;
      const { total: abnormalTotal } = res2;
      const tabList: tabItem[] = [{
        name: 'rollback', label: window.i18n.t('版本回滚'), total, data: [],
      }];
      // 无异常主机无需展示
      if (abnormalTotal) {
        tabList.push({
          name: 'abnormalHost', label: window.i18n.t('异常agent个数', ['Agent']), total: abnormalTotal, data: [],
        });
      }
      this.targetTabList.splice(0, this.targetTabList.length, ...tabList);
      this.formatTableDataResult(res1, params);
    });
  }
  // 灰度策略 - 回滚tab数据
  public async getRollbackPreview() {
    const { current, limit } = this.pagination;
    const params: Dictionary = {
      page: current,
      pagesize: limit,
      policy_id: this.ruleId,
      conditions: this.getConditions(),
    };
    const res = await PluginStore.getRollbackPreview(params);
    res.params = params;
    return Promise.resolve(res);
  }
  // 灰度策略 - 展示agent异常主机
  public async getAgentAbnormalHost() {
    const { current, limit } = this.pagination;
    const { scope } = PluginStore.strategyData;
    const params: Dictionary = {
      page: current,
      pagesize: limit,
      scope,
      conditions: [{ key: 'status', value: ['TERMINATED', 'NOT_INSTALLED', 'UNKNOWN'] }],
    };
    const res = await PluginStore.getAbnormalHost(params);
    res.params = params;
    return Promise.resolve(res);
  }

  // 立即执行 ps - 灰度策略打算复用主策略的接口
  public async handleExec() {
    if (this.isPolicyOperateType) {
      // 策略操作
      this.handleOperatePolicy(this.jobType);
    } else {
      this.executeLoading = true;
      const params: Dictionary = this.getParams();
      let res: IPolicyOperate;
      if (this.jobType === 'create') {
        // 创建策略
        res = await PluginStore.createPolicy(params);
      } else if (this.isManualType) {
        // 手动操作插件
        params.job_type = this.jobType;
        params.plugin_name = PluginStore.strategyData.plugin_info?.name;
        res = await PluginStore.pluginOperate(params);
      } else {
        // 策略更新: this.isPolicyUpdateType
        res = await PluginStore.updatePolicy({ pk: `${this.ruleId}`, params });
      }
      this.afterOperate(res);
    }
  }
  // 策略操作
  private async handleOperatePolicy(type: string) {
    this.executeLoading = true;
    const res = await PluginStore.operatePolicy({
      policy_id: this.ruleId,
      op_type: type.toUpperCase(),
    });
    this.afterOperate(res);
  }
  // 强制删除策略
  private async deletePolicy() {
    this.deleteLoading = true;
    const res = await PluginStore.operatePolicy({
      policy_id: this.ruleId,
      op_type: 'DELETE',
    });
    this.afterOperate(res);
  }

  public getParams() {
    const { name, scope, configs,  params, plugin_info: pluginInfo } = PluginStore.strategyData;
    scope.nodes = scope.nodes.map((node) => {
      delete node.children;
      return node;
    });
    const res: Dictionary = { name, scope };
    if (this.isGrayRule && this.isRuleCreateType) {
      res.pid = this.ruleId;
    }
    if (!manualNotSteps.includes(this.jobType)) {
      res.steps = [{
        id: pluginInfo?.name,
        type: 'PLUGIN',
        configs,
        params,
      }];
    }
    return res;
  }
  public getConditions() {
    const conditions: { key: string, value: string | any[] }[]  = [];
    this.searchSelectValue.forEach((item) => {
      if (Array.isArray(item.values)) {
        const valuesArr = item.values.map(v => v.id);
        conditions.push({ key: item.id, value: valuesArr });
      } else {
        conditions.push({ key: 'query', value: item.name });
      }
    });
    return conditions;
  }
  // 前端分页筛选
  public frontFilterTableData() {
    const { current, limit } = this.pagination;
    const currentTab = this.targetTabList.find(item => item.name === this.tabActive);
    let copyTabData = [...(currentTab?.data || [])];
    const conditions: Dictionary = {};
    this.getConditions().reduce((obj, item) => {
      obj[item.key] = item.value;
      return obj;
    }, conditions);
    // 业务、云区域、操作系统为大范围, agent状态为小范围
    const filterKeys = ['bk_biz_name', 'bk_cloud_id', 'os_type', 'status'];
    filterKeys.forEach((key) => {
      let conditionItem = conditions[key];
      if (conditionItem) {
        // 操作系统 - 其它（none）todo
        if (key === 'os_type') {
          conditionItem = conditionItem.map((item: string) => this.osMap[item] || item);
        }
        if (key === 'status') {
          conditionItem = conditionItem.map((item: string) => item.toLowerCase());
        }
        copyTabData = copyTabData.filter((item: Dictionary) => conditionItem.some((value: any) => item[key] === value));
      }
    });
    this.pagination.count = copyTabData.length;
    const start = (current - 1) * limit;
    const end = Math.min(copyTabData.length, start + limit);
    this.data = copyTabData.slice(start, end);
    return this.data;
  }
  public afterOperate(res: any) {
    if (res.job_id) {
      MainStore.updateEdited(false);
      this.$router.push({ name: 'taskDetail', params: { taskId: res.job_id, routerBackName: 'taskList' } });
    }
    if (res.deleted) {
      if (res.operate_results && res.operate_results.length) {
        MainStore.updateEdited(false);
        this.$router.push({
          name: 'taskList',
          params: {
            taskIds: res.operate_results.map((item: Dictionary) => item.job_id),
          },
        });
      } else {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('操作策略成功', [this.isDeleteGrayType ? this.$t('删除') : this.$t('强制删除')]),
        });
        MainStore.updateEdited(false);
        this.$router.go(-1);
      }
    }
    this.executeLoading = false;
    this.deleteLoading = false;
  }
}
</script>
<style lang="postcss" scoped>
.primary {
  color: #3a84ff;
}
.btn {
  cursor: pointer;
}
.perform-preview {
  padding: 0 30px;
  .completion-btn {
    margin-top: 24px;
  }
  .table-status {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 10px 0 0;
    height: 41px;
    background: #f0f1f5;
    border: 1px solid #dcdee5;
    border-bottom: 0;
    .tab-wrapper {
      position: relative;
      flex: 1;
      height: 100%;
    }
    .preview-tab {
      position: absolute;
      top: -1px;
      left: -1px;
      width: 100%;
      z-index: 50;
      .panel-content {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        padding-bottom: 13px;
        height: 42px;
        line-height: 17px;
        &.panel-error-content {
          .panel-name {
            color: #ea3636;
          }
          .panel-total {
            color: #ea3636;
            background: #f2dfdf;
          }
        }
      }
      .panel-name {
        font-size: 13px;
        color: #313238;
      }
      .panel-total {
        margin-left: 6px;
        padding: 0 7px;
        border-radius: 9px;
        font-size: 12px;
        color: #63656e;
        background: #dcdee5;
      }
      /deep/ .bk-tab-header>.bk-tab-label-wrapper>.bk-tab-label-list>.bk-tab-label-item {
        &.active .panel-content {
          background: #fafbfd;
        }
        &.active .panel-content,
        &:hover:not(.is-disabled) .panel-content {
          margin-top: -1px;
          padding-bottom: 12px;
          border-top: 3px solid #3a84ff;
          .panel-name,
          .panel-total {
            color: #3a84ff;
          }
          .panel-total {
            background: #e1ecff;
          }
          &.panel-error-content {
            border-top: 3px solid #ea3636;
            .panel-name,
            .panel-total {
              color: #ea3636;
            }
          }
        }
      }
      /deep/ .bk-tab-section {
        display: none;
      }
      .bk-tab-label .bk-button {
        margin-bottom: -6px;
        line-height: 1;
        border: 0;
        background: transparent;
        cursor: not-allowed;
      }
      /deep/ .bk-button-loading div {
        background-color: #63656e;
      }
    }
    .count {
      color: #63656e;
    }
    .filter-content {
      display: inline-flex;
      align-items: center;
      color: #63656e;
    }
    .vertical-line {
      margin: 0 5px;
    }
    .filter-num {
      font-weight: bold;
      cursor: pointer;
    }
    .running {
      color: #3fc06d;
    }
    .terminated {
      color: #ea3636;
    }
  }
  .policy-link-btn {
    .nodeman-icon {
      display: none;
    }
    &:hover .nodeman-icon {
      display: inline;
    }
  }
}
</style>
