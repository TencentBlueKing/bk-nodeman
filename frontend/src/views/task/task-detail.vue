<template>
  <div class="task-detail-wrapper" v-bkloading="{ isLoading: loading }">
    <template v-if="!loading">
      <div class="nodeman-navigation-content mb20">
        <span class="content-icon" @click="handleBack">
          <i class="nodeman-icon nc-back-left"></i>
        </span>
        <span class="content-header">{{ navTitle }}</span>
        <div class="content-subtitle" v-if="taskStatus">
          <span :class="`tab-badge bg-${taskStatus}`">{{ titleStatusMap[taskStatus] || $t('状态未知') }}</span>
        </div>
      </div>
      <Tips class="mb20" v-if="isManualType">
        <template #default>
          <p>
            {{ commandTip }}
          </p>
        </template>
      </Tips>
      <section class="detail-option clearfix">
        <bk-button
          class="fl"
          hover-theme="danger"
          :loading="stopLoading"
          :disabled="staticDetal.running === 0 || stopLoading"
          @click="handleTaskStop">
          {{ stopLoading ? '' : $t('终止') }}
        </bk-button>
        <bk-button
          class="fl ml10"
          :loading="retryLoading"
          :disabled="staticDetal.failed === 0 || retryLoading"
          @click.stop="handleTaskRetry">
          {{ $t('失败重试')}}
        </bk-button>
        <bk-dropdown-menu
          class="fl"
          trigger="click"
          ref="dropdownCopy"
          font-size="medium"
          :disabled="copyLoading"
          @show="copyDropdownShow('copy')"
          @hide="copyDropdownHide('copy')">
          <bk-button class="copy-dropdown-btn" type="primary" slot="dropdown-trigger" :loading="copyLoading">
            <span class="icon-down-wrapper">
              <span>{{ $t('复制') }}</span>
              <i :class="['bk-icon icon-angle-down', { 'icon-flip': isShowCopy }]"></i>
            </span>
          </bk-button>
          <ul class="bk-dropdown-list" slot="dropdown-content">
            <li v-for="copyType in copyTypeList" :key="copyType.key">
              <a href="javascript:" @click.prevent.stop="handleCopy(copyType)">{{ copyType.name }}</a>
            </li>
          </ul>
        </bk-dropdown-menu>
        <bk-search-select
          class="fr task-filter-select"
          split-code=","
          :show-condition="false"
          :placeholder="$t('请输入')"
          :data="searchSelectData"
          v-model="searchSelectValue"
          @change="handleSearchSelectChange">
        </bk-search-select>
      </section>
      <section class="task-table" v-bkloading="{ isLoading: tableLoading }">
        <div class="table-header">
          <div class="table-header-left">
            <span class="package-name">{{ jobTypeDisplay }}</span>
            <i18n path="机器数量" class="package-selection">
              <span class="selection-num">{{ staticDetal.all }}</span>
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
                <span class="dot"
                      v-if="item.status === 'running' && index === (treeShakingStatus.length - 1)">...</span>
              </span>
            </template>
          </div>
        </div>

        <bk-table
          ref="agentTable"
          row-key="innerIp"
          :data="tableList"
          :pagination="pagination"
          :limit-list="pagination.limitList"
          :class="`head-customize-table ${ fontSize }`"
          :span-method="colspanHandle"
          @page-change="pageChange"
          @page-limit-change="paginationChange"
          @select="tableSelectHandle"
          @select-all="tableSelectHandle">
          <!-- <bk-table-column
            class-name="row-select"
            type="selection"
            width="40"
            :resizable="false"
            :reserve-selection="true"
            :selectable="selectAbleHandle">
          </bk-table-column> -->
          <bk-table-column class-name="row-ip" label="IP" prop="innerIp" :resizable="false">
            <template #default="{ row }">
              {{ row.innerIp | filterEmpty }}
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('云区域')" prop="bkCloudName" :resizable="false">
            <template #default="{ row }">
              {{ row.bkCloudName | filterEmpty }}
            </template>
          </bk-table-column>
          <bk-table-column min-width="100" :label="$t('业务')" prop="bkBizName" :resizable="false">
            <template #default="{ row }">
              {{ row.bkBizName | filterEmpty }}
            </template></bk-table-column>
          <bk-table-column min-width="100" :label="$t('安装方式')" prop="isManual" :resizable="false">
            <template #default="{ row }">
              {{ installTypeCell(row.isManual) }}
            </template>
          </bk-table-column>
          <bk-table-column
            prop="status"
            :label="$t('执行状态')"
            min-width="220"
            :render-header="renderFilterHeader">
            <template #default="{ row }">
              <!-- is_running 区分已忽略且正在别的任务下执行的情况 -->
              <div class="col-execution">
                <loading-icon v-if="row.status === 'running'"></loading-icon>
                <span v-else :class="`execut-mark execut-${ row.status }`"></span>
                <span
                  v-if="row.status === 'filtered'"
                  :class="['execut-text', { 'has-icon': row.exception && row.exception === 'is_running' }]"
                  :title="filteredTitle(row)"
                  @click.stop="filterrdHandle(row)">
                  {{ `${titleStatusMap[row.status]} ` }}
                  ({{ row.statusDisplay | filterEmpty }}<i
                    v-if="row.exception && row.exception === 'is_running'"
                    class="nodeman-icon nc-icon-audit filtered-icon">
                  </i>)
                </span>
                <span v-else>{{ row.statusDisplay | filterEmpty }}</span>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column
            prop="colspaOpera"
            :width="(hasCommandTaskType ? 158 : 93) + (fontSize === 'large' ? 20 : 0)"
            :label="$t('操作')"
            :resizable="false">
            <template #default="{ row }">
              <!-- 命令查看 手动类型 && ( 安装 >=2 | 重装 >= 1 | 升级 >=1 (仅windows有) | 卸载 ) -->
              <template v-if="hasCommandTaskType">
                <bk-button
                  text
                  class="mr10"
                  v-if="row.nodeId >= vewCommandStep || row.status === 'success'"
                  theme="primary"
                  :disabled="commandLoading"
                  @click="viewCommand(row)">
                  {{ commandText }}
                </bk-button>
              </template>
              <bk-button
                class="mr10"
                text
                v-if="row.status !== 'filtered' && !row.filterHost"
                theme="primary"
                @click.stop="handleViewLogDetail(row)">
                {{ $t('查看日志') }}
              </bk-button>
              <loading-icon v-if="row.loading"></loading-icon>
              <template v-else-if="!row.loading && !row.filterHost">
                <bk-button
                  text
                  v-if="row.status === 'failed'"
                  theme="primary"
                  @click="handleTaskRetry([row])">
                  {{ $t('重试') }}
                </bk-button>
                <bk-button
                  text
                  v-if="row.status === 'running'"
                  theme="primary"
                  @click="handleTaskStop([row])">
                  {{ $t('终止') }}
                </bk-button>
              </template>
            </template>
          </bk-table-column>
          <!--自定义字段显示列-->
          <bk-table-column
            key="setting"
            prop="colspaSetting"
            :render-header="renderHeader"
            width="42"
            :resizable="false">
          </bk-table-column>
        </bk-table>
      </section>
    </template>
    <bk-sideslider
      ext-cls="commands-slider"
      transfer
      quick-close
      :width="620"
      :is-show.sync="slider.show"
      :title="slider.title">
      <div slot="content" class="commands-wrapper" v-bkloading="{ isLoading: commandLoading }">
        <template v-if="slider.hostSys === 'WINDOWS'">
          <p class="guide-title">{{ $t('slider安装windows', { type: 'Agent' }) }}</p>
          <p class="guide-title">
            1. {{ $t('windowsStrategy1Before') }}
            <span class="guide-link"> curl.exe </span>
            {{ $t('windowsStrategy1After') }}
          </p>
          <p class="guide-title">2. {{ $t('windowsStrategy2') }}</p>
        </template>
        <p class="guide-title" v-else>
          {{ $t('slider安装title', { type: operateHost, job: isUninstallType ? $t('卸载') : $t('安装') }) }}
        </p>
        <p class="guide-title">
          <template v-if="slider.hostSys === 'WINDOWS'">3. {{ $t('windowsStrategy3') }} </template>
          <template v-else>{{ $t('linuxStrategy1') }}</template>
          <bk-popover
            ref="popover"
            trigger="click"
            theme="light silder-guide"
            placement="bottom-start">
            <span class="guide-link pointer">{{ $t('网络策略开通指引') }}</span>
            <template #content>
              <StrategyTemplate
                v-if="slider.show"
                class="operation-tips"
                :host-type="slider.hostType"
                :host-list="hostList">
              </StrategyTemplate>
            </template>
          </bk-popover>
        </p>
        <Tips class="mb20" v-if="slider.hostSys !== 'WINDOWS'">
          <template #default>
            <p>
              {{ $t('请将指令中的') }}
              <span class="tips-text-decs">{{ $t('账号') }}</span>
              <span class="tips-text-decs">{{ $t('端口') }}</span>
              <span class="tips-text-decs">{{ $t('密码密钥') }}</span>
              {{ $t('替换成') }}
              <span class="tips-text-decs">{{ $t('真实数据') }}</span>
              {{ $t('再执行') }}
            </p>
          </template>
        </Tips>
        <template v-if="!commandError">
          <ul class="commands-list" v-if="commandData.length">
            <li class="commands-item"
                v-for="(item, index) in commandData"
                :key="item.cloudId">
              <p class="commands-title mb10" v-if="!slider.isSingle">{{ item.cloudName }}</p>
              <div :class="['command-conatainer', { 'fold': item.isFold, 'single': slider.isSingle }]">
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div v-html="slider.isSingle ? item.command : item.totalCommands"
                     class="commands-left"
                     :ref="`commanad${ item.cloudId }`">
                </div>
                <div class="commands-right">
                  <p>
                    <i class="nodeman-icon nc-copy command-icon" v-bk-tooltips="{
                      delay: [300, 0],
                      content: $t('复制命令')
                    }" @click="copyCommand(item, index)"></i>
                  </p>
                </div>
              </div>
            </li>
          </ul>
          <ExceptionCard v-else type="dataAbnormal"></ExceptionCard>
        </template>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import tableHeaderMixins from '@/components/common/table-header-mixins';
import Tips from '@/components/common/tips.vue';
import ColumnSetting from '@/components/common/column-setting';
import StrategyTemplate from '@/components/common/strategy-template';
import ExceptionCard from '@/components/exception/exception-card';
import pollMixin from '@/common/poll-mixin';
import { debounce, copyText, toHump, isEmpty } from '@/common/util';
import { MainStore, TaskStore, AgentStore } from '@/store';
import routerBackMixin from '@/common/router-back-mixin';

export default {
  name: 'TaskDetail',
  components: {
    Tips,
    StrategyTemplate,
    ExceptionCard,
  },
  mixins: [tableHeaderMixins, pollMixin, routerBackMixin],
  props: {
    taskId: {
      type: [String, Number],
      default: '',
    },
    status: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      loading: false,
      tableLoading: false,
      stopLoading: false,
      retryLoading: false,
      isShowCopy: false,
      copyDisabled: true,
      taskStatus: '',
      loadMessage: true,
      installReg: /^(?!re)(install)/ig,
      staticDetal: {
        failed: 0,
        filtered: 0,
        success: 0,
        running: 0,
        pending: 0,
        all: 0,
      },
      jobType: '',
      jobTypeDisplay: '',
      timestamp: '',
      // 表格筛选
      selected: [],
      filterData: [
        { name: 'IP', type: 'innerIp', id: 'ip' },
        {
          name: this.$t('执行状态'),
          id: 'status',
          multiable: true,
          children: [
            { id: 'PENDING', name: this.$t('等待执行'), checked: false },
            { id: 'RUNNING', name: this.$t('正在执行'), checked: false },
            { id: 'SUCCESS', name: this.$t('执行成功'), checked: false },
            { id: 'FAILED', name: this.$t('执行失败'), checked: false },
            { id: 'FILTERED', name: this.$t('已忽略'), checked: false }, // 老任务保留已忽略， 新的任务都已改为报错处理
          ],
        },
      ],
      pagination: {
        limit: 50,
        current: 1,
        count: 0,
        limitList: [50, 100, 200],
      },
      tableList: [],
      selectedHosts: [],
      titleStatusMap: {
        running: this.$t('正在执行'),
        failed: this.$t('执行失败'),
        part_failed: this.$t('部分失败'),
        success: this.$t('执行成功'),
        stop: this.$t('已终止'),
        pending: this.$t('等待执行'),
        terminated: this.$t('已终止'),
        filtered: this.$t('已忽略'),
      },
      // 搜索防抖
      getDetailListDebounce() {},
      statusMap: {
        success: this.$t('个成功'),
        failed: this.$t('个失败'),
        filtered: this.$t('个忽略'),
        running: this.$t('个执行中'),
        pending: this.$t('个等待执行'),
      },
      ipRegx: /^((\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.){3}(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$/,
      copyLoading: false,
      copyTypeList: [
        { name: this.$t('所有IP'), key: '' },
        { name: this.$t('被忽略IP'), key: 'filtered' },
        { name: this.$t('失败IP'), key: 'failed' },
        { name: this.$t('成功IP'), key: 'success' },
      ],
      slider: {
        show: false,
        title: '',
        isSingle: false,
        hostType: '',
        hostSys: '',
      },
      commandLoading: false,
      commandData: [],
      commandError: false,
      // callBackUrl: window.PROJECT_CONFIG.BKAPP_NODEMAN_CALLBACK_URL
    };
  },
  computed: {
    fontSize() {
      return MainStore.fontSize;
    },
    routetParent() {
      return TaskStore.fontSize;
    },
    navTitle() {
      return `${this.$t('任务详情')} ${this.jobTypeDisplay} ${this.timestamp}`;
    },
    // 获取个数非零的状态
    treeShakingStatus() {
      return Object.keys(this.staticDetal).filter(key => key !== 'all' && !!this.staticDetal[key])
        .map(key => ({
          status: key,
          value: this.staticDetal[key],
        }));
    },
    // 操作的主机或任务类型 Agent | Proxy | Plugin
    operateHost() {
      const res = /(agent)|(proxy)|(plugin)/ig.exec(this.jobType);
      return res ? res[0] : '';
    },
    // 是否为手动类型安装机器
    isManualType() {
      return this.tableList.some(row => row.isManual);
    },
    // 能查看命令的任务类型
    hasCommandTaskType() {
      if (!this.operateHost || this.operateHost === 'plugin' || !this.isManualType) {
        return false;
      }
      // return /(^(?!UN)(INSTALL))|(REINSTALL)|(UPGRADE)/ig.test(this.jobType)
      return /(INSTALL)|(REINSTALL)|(UPGRADE)/ig.test(this.jobType);
    },
    // 能查看命令的步骤
    vewCommandStep() {
      // const regRes = /(^(?!UN)(INSTALL))|(REINSTALL)|(UPGRADE)/ig.exec(this.jobType)
      const regRes = /(INSTALL)|(REINSTALL)|(UPGRADE)/ig.exec(this.jobType);
      const taskType = regRes ? regRes[0] : '';
      if (taskType === 'install') {
        return /UN/ig.test(this.jobType) ? 0 : 2;
      } if (taskType === 'reinstall' || taskType === 'upgrade') {
        return 1;
      }
      return NaN;
    },
    isUninstallType() {
      return /UN/ig.test(this.jobType);
    },
    commandText() {
      return this.isUninstallType ? this.$t('卸载命令btn') : this.$t('命令btn');
    },
    commandTip() {
      return this.isUninstallType ? this.$t('手动卸载任务Tips') : this.$t('手动安装任务Tips');
    },
    hasFaileHosts() {
      return this.selectedHosts.some(item => item.status === 'stop' || item.status === 'failed');
    },
    hasRunningHosts() {
      return this.selectedHosts.some(item => item.status === 'running');
    },
    hostList() {
      const list = this.tableList.map(item => ({
        bk_cloud_id: item.bkCloudId,
        bk_cloud_name: item.bkCloudName,
        ap_id: item.apId,
        inner_ip: item.innerIp,
      }));
      list.sort((a, b) => a.bk_cloud_id - b.bk_cloud_id);
      return list;
    },
  },
  watch: {
    searchSelectValue: {
      handler() {
        this.getDetailListDebounce();
      },
      deep: true,
    },
    taskStatus(v) {
      this.runingQueue = v === 'running' ? [1] : [];
    },
  },
  created() {
    if (this.status) {
      // 会自动触发watch进行搜索
      this.numFilterHandle(this.status);
    } else {
      this.getHistoryTaskDetail();
    }
  },
  mounted() {
    this.getDetailListDebounce = debounce(300, this.pageChange);
  },
  beforeRouteLeave(to, from, next) {
    MainStore.setToggleDefaultContent(false); // 带返回的路由背景置为白色
    next();
  },
  methods: {
    /**
     * 拉取主机执行结果统计数量 及 主机列表
     */
    async getHistoryTaskDetail() {
      this.tableLoading = true;
      const res = await TaskStore.requestHistoryTaskDetail({
        jobId: this.taskId,
        params: this.getCommonParams(),
      });
      if (res) {
        const { list, statistics, status, jobType, jobTypeDisplay, startTime, total, ipFilterList } = res;
        list.forEach((item) => {
          item.loading = false;
        });
        this.taskStatus = status ? status.toLowerCase() : '';
        this.jobType = toHump((jobType || '').toLowerCase());
        this.jobTypeDisplay = jobTypeDisplay || '--';
        this.timestamp = startTime || '';
        this.tableList.splice(0, this.tableList.length, ...list);
        this.pagination.count = total || 0;
        this.handleStatistics(statistics, ipFilterList);
      }
      if (this.isManualType) {
        AgentStore.getCloudList();
      }
      this.tableLoading = false;
    },
    handleStatistics(statistics, ipFilterList) {
      // const staticList = []
      if (statistics) {
        const { successCount, failedCount, filterCount, runningCount, pendingCount, totalCount } = statistics;
        Object.assign(this.staticDetal, {
          failed: failedCount || 0,
          filtered: filterCount || 0,
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
    },
    getCommonParams() {
      const params = {
        page: this.pagination.current,
        pagesize: this.pagination.limit,
      };
      const conditions = [];
      const searchObj = this.searchSelectValue.reduce((obj, item) => {
        if (item.values) {
          const valueArr = item.values.map(value => value.id);
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
      // 多IP搜索传参
      Object.entries(searchObj).forEach((item) => {
        const [key, val] = item;
        const value = [...new Set(val)];
        conditions.push({ key: key === 'status' ? key : 'ip', value: key === 'status' ? value : value.join(',') });
      });
      if (conditions.length) {
        params.conditions = conditions;
      }
      return params;
    },
    /**
     * 处理轮询的数据
     */
    async handlePollData() {
      const res = await TaskStore.requestHistoryTaskDetail({
        jobId: this.taskId,
        params: this.getCommonParams(),
      });
      if (res) {
        const { list, statistics, status, jobType, jobTypeDisplay, total } = res;
        this.taskStatus = status ? status.toLowerCase() : '';
        this.jobType = toHump((jobType || '').toLowerCase());
        this.jobTypeDisplay = jobTypeDisplay || '--';
        this.pagination.count = total || 0;
        // 带筛选的条件会导致列表为空
        list.forEach((item) => {
          const current = this.tableList.find(row => row.instanceId === item.instanceId);
          item.loading = current ? current.loading : false;
        });
        this.tableList.splice(0, this.tableList.length, ...list);
        this.handleStatistics(statistics);
      }
      return res;
    },
    /**
     * 表格相关
     */
    pageChange(page) {
      this.pagination.current = page || 1;
      this.getHistoryTaskDetail();
    },
    paginationChange(limit) {
      this.pagination.limit = limit || 10;
      this.getDetailListDebounce();
    },
    copyDropdownShow() {
      this.isCopyDropdownShow = true;
    },
    copyDropdownHide() {
      this.isCopyDropdownShow = false;
    },
    async handleCopy(type) {
      this.$refs.dropdownCopy.hide();
      const params = {
        pagesize: -1,
      };
      if (type.key) {
        params.conditions = [
          { key: 'status', value: [type.key.toUpperCase()] },
        ];
      }
      this.copyLoading = true;
      const res = await TaskStore.requestHistoryTaskDetail({
        jobId: this.taskId,
        params,
      });
      if (res) {
        if (res.list ? res.list.length : false) {
          const ipStr = res.list.map(item => item.innerIp).join('\n');
          copyText(ipStr, () => {
            this.$bkMessage({
              theme: 'success',
              message: this.$t('IP复制成功', { num: res.list.length }),
            });
          });
        }
      }
      this.copyLoading = false;
    },
    handleViewLogDetail(row) {
      this.$router.push({
        name: 'taskLog',
        params: {
          taskId: this.taskId,
          instanceId: row.instanceId.toString(),
        },
      });
    },
    async handleTaskStop(selction = []) {
      const isBatch = !selction.length;
      if (!isBatch && selction.find(item => item.loading)) {
        return false;
      }
      this.stopLoading = true;
      const data = isBatch ? [] : selction;
      this.setRowsLoading(data, true);
      const res = await TaskStore.requestTaskStop({
        jobId: this.taskId,
        params: { instance_id_list: data.map(item => item.instanceId) },
      });
      if (res.result) {
        this.staticDetal.failed += data.length;
        this.staticDetal.running -= data.length;
        this.handleStatistics();
        this.setRowsStatus(data, 'failed');
      }
      this.stopLoading = false;
      this.setRowsLoading(data, false);
      // 带筛选条件时需要重新加载列表
      if (res.result) {
        await this.handlePollData();
      }
    },
    /**
     * 重试
     * proxy 类型都是单台机器操作
     *  1. 安装 - 回填信息至安装页
     *  2. 其他 - 直接重试&接口操作
     * agent 有批量操作，且可能包含手动、远程两种安装类型
     *  1. 安装 - 回填信息至安装页（只存在一种安装类型）
     *  2. 重装&升级 - ？（等设计）
     *  3. 其他 - 直接重试&接口操作
     */
    async handleTaskRetry(selction = []) {
      const isBatch = !selction.length;
      const data = isBatch ? [] : selction;
      if (!isBatch && selction.find(item => item.loading)) {
        return false;
      }
      this.retryLoading = true;
      this.setRowsLoading(data, true);
      const res = await TaskStore.requestTaskRetry({
        jobId: this.taskId,
        params: { instance_id_list: data.map(item => item.instanceId) },
      });
      this.retryLoading = false;
      if (res.result) {
        this.taskStatus = 'running';
        this.setRowsStatus(data, 'pending');
        this.staticDetal.failed -= data.length;
        this.staticDetal.pending += data.length;
        this.handleStatistics();
      }
      this.setRowsLoading(data, false);
      // 带筛选条件时需要重新加载列表
      if (res.result) {
        await this.handlePollData();
      }
      // }
    },
    setRowsStatus(data, status) {
      data.forEach((row) => {
        if (status === 'pending' && row.status === 'failed') {
          row.status = status;
          row.statusDisplay = this.$t('等待执行');
        } else if (status === 'failed' && (row.status === 'pending' || row.status === 'running')) {
          row.status = status;
          row.statusDisplay = this.$t('已终止');
        }
      });
    },
    setRowsLoading(data, isLoading) {
      data.forEach((row) => {
        row.loading = isLoading;
      });
    },
    /**
     * 返回
     */
    handleBack() {
      this.routerBack();
    },
    numFilterHandle(status) {
      if (!status) return;
      const item = this.filterData.find(item => item.id === 'status').children.find(item => item.id === status);
      // mixin 方法
      this.handleSearchSelectChange([
        {
          name: this.$t('执行状态'),
          id: 'status',
          values: [item],
        },
      ]);
      this.searchSelectValue.splice(0, this.searchSelectValue.length);
      this.handlePushValue('status', [item], false);
    },
    /**
     * 已忽略且正在运行的主机跳转
     */
    filterrdHandle(row) {
      if (row.jobId && row.exception && row.exception === 'is_running') {
        this.$router.push({
          name: 'taskLog',
          params: {
            taskId: row.jobId,
            hostInnerIp: row.innerIp,
          },
        });
      }
    },
    filteredTitle(row) {
      return `${this.titleStatusMap[row.status]} ${(row.statusDisplay || '').replace(/\s+/g, ' ')}`;
    },
    // 每次点击都需要获取最新的命令
    async requestCommandData(row) {
      if (!this.commandLoading) {
        this.commandLoading = true;
        const params = {
          bk_host_id: row ? row.bkHostId : -1,
        };
        if (this.isUninstallType) {
          params.is_uninstall = true;
        }
        const res = await TaskStore.requestCommands({
          jobId: this.taskId,
          params,
        });
        if (res) {
          const data = [];
          if (row) {
            const cloudCommand = res[row.bkCloudId];
            const curCommand = cloudCommand ? cloudCommand.ipsCommands.find(item => item.ip === row.innerIp) : null;
            this.slider.hostSys = curCommand ? curCommand.osType : '';
            if (curCommand) {
              data.push(Object.assign({
                isFold: false,
                cloudId: row.cloudId,
              }, curCommand));
            }
          } else {
            Object.keys(res).forEach((key) => {
              const commandItem = {
                isFold: false,
                // eslint-disable-next-line radix
                cloudId: parseInt(key),
                cloudName: '',
              };
              // eslint-disable-next-line radix
              if (parseInt(key) === window.PROJECT_CONFIG.DEFAULT_CLOUD) {
                commandItem.cloudName = this.$t('直连区域');
              } else {
                const cloud = AgentStore.cloudList.find(item => `${item.bkCloudId}` === key
                              || item.bkCloudId === window.PROJECT_CONFIG.DEFAULT_CLOUD);
                commandItem.cloudName = cloud ? cloud.bkCloudName : key;
              }
              data.push(Object.assign(commandItem, res[key]));
            });
          }
          this.commandData = data;
        }
        this.commandError = !res;
        this.commandLoading = false;
        return res;
      }
      return false;
    },
    async copyCommand(row, index) {
      if (!row || this.commandLoading) {
        return false;
      }
      const hasCommand = Object.prototype.hasOwnProperty.call(row, 'isFold'); // dialog里的复制不需要重新加载数据
      let res = true;
      if (!hasCommand) {
        res = await this.requestCommandData(row);
      }
      let commandStr = '';
      if (hasCommand) {
        const ref = this.$refs[`commanad${row.cloudId}`];
        commandStr = ref ? ref[index].textContent : '';
      } else {
        const cloud = this.commandData.find(item => item.cloudId === row.bkCloudId);
        const commandList = cloud ? cloud.ipsCommands : [];
        const commandItem = commandList.find(item => item.ip === row.innerIp);
        commandStr = commandItem ? commandItem.command.replace(/<[^>]+>/gi, '') : '';
      }
      if (res && commandStr) {
        copyText(commandStr, () => {
          this.$bkMessage({
            theme: 'success',
            message: this.$t('命令复制成功'),
          });
        });
      }
    },
    viewCommand(row) {
      this.commandError = false;
      this.slider.show = true;
      this.slider.isSingle = !!row;
      if (row) {
        if (this.operateHost === 'Proxy') {
          this.slider.hostType = this.operateHost;
        } else {
          this.slider.hostType = row.bkCloudId === window.PROJECT_CONFIG.DEFAULT_CLOUD ? 'Agent' : 'Pagent';
        }
      } else {
        this.slider.hostType = this.operateHost === 'Proxy' ? this.operateHost : 'mixed';
      }
      this.slider.title =  this.$t('手动操作sliderTitle', {
        ip: row ? row.innerIp : '',
        job: this.$t(this.isUninstallType ? '卸载' : '安装'),
      });
      this.requestCommandData(row);
    },
    toggleCommand(row) {
      row.isFold = !row.isFold;
    },
    tableSelectHandle(selection) {
      this.selectedHosts = selection;
    },
    selectAbleHandle(row) {
      return row.status !== 'filtered' && row.status !== 'pendding';
    },
    /**
     * 自定义字段显示列
     * @param {createElement 函数} h 渲染函数
     */
    renderHeader(h) {
      return h(ColumnSetting);
    },
    /**
     * 合并最后两列
     */
    colspanHandle({  column }) {
      if (column.property === 'colspaOpera') {
        return [1, 2];
      } if (column.property === 'colspaSetting') {
        return [0, 0];
      }
    },
    installTypeCell(cell) {
      if (isEmpty(cell)) {
        return '--';
      }
      return cell ? this.$t('手动') : this.$t('远程');
    },
  },
};
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
  .nodeman-navigation-content {
    @mixin layout-flex row, center;
    .content-icon {
      position: relative;
      height: 20px;
      line-height: 20px;
      top: -4px;
      margin-left: -7px;
      font-size: 28px;
      color: $primaryFontColor;
      cursor: pointer;
    }
    .content-header {
      font-size: 16px;
      color: $headerColor;
    }
    .content-subtitle {
      display: flex;
      margin-left: 10px;
      font-size: 12px;
      color: #979ba5;
    }
    .tab-badge {
      padding: 0 4px;
      line-height: 16px;
      border-radius: 2px;
      font-weight: 600;
      color: #fff;
    }
  }
  .task-detail-wrapper {
    min-height: calc(100vh - 60px);
    padding: 20px 60px 30px 60px;
    overflow: auto;
    .detail-option {
      margin: 0 0 16px 0;
      .fl + .fl {
        margin-left: 10px;
      }
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
    .tips-text-decs {
      color: #313238;
    }
    .task-filter-select {
      width: 500px;
      background: #fff;
    }
    .task-table {
      margin-top: 14px;
    }
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
    .filtered {
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
    .dot {
      position: relative;
      display: inline-block;
      font-size: 14px;
      vertical-align: bottom;
      color: transparent;
      overflow: hidden;
      &::after {
        position: absolute;
        left: 0;
        top: 0;
        display: inline-block;
        content: "...";
        width: 0;
        height: 100%;
        z-index: 5;
        color: #63656e;
        vertical-align: bottom;
        overflow: hidden;
        animation: dot 3s infinite step-start;
      }
    }
  }
  /deep/ .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  /deep/ .row-ip .cell {
    padding-left: 24px;
  }
  /deep/ .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  .guide-title {
    margin: 0 0 14px 0;
    .guide-link {
      color: #3a84ff;
      &.pointer {
        cursor: pointer;
      }
    }
  }
  .commands-slider {
    .commands-wrapper {
      padding: 24px 30px;
      min-height: calc(100vh - 52px);
      overflow: auto;
    }
    .commands-item {
      margin-bottom: 20px;
      &:last-child {
        margin-bottom: 0;
      }
    }
    .commands-title {
      font-size: 14px;
      color: #63656e;
    }
    .command-conatainer {
      position: relative;
      padding: 12px 28px 16px 20px;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      background: #fafbfd;
      .commands-left {
        width: 100%;
        max-height: 128px;
        min-height: 22px;
        line-height: 18px;
        font-size: 12px;
        color: #979ba5;
        overflow-x: hidden;
        overflow-y: auto;
        word-break: break-all;
        >>> span {
          color: #313238;
        }
      }
      &.fold {
        padding: 7px 10px;
        .commands-left {
          padding-right: 56px;
          white-space: nowrap;
          text-overflow: ellipsis;
          overflow: hidden;
        }
      }
      &.single .commands-left {
        max-height: none;
      }
      .commands-right {
        position: absolute;
        right: 5px;
        bottom: 5px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        width: 46px;
        line-height: 18px;
        font-size: 17px;
        text-align: right;
      }
      .command-icon {
        color: #979ba5;
        cursor: pointer;
        &:hover {
          color: #63656e;
        }
      }
    }
  }
  .operation-tips {
    max-height: 600px;
    overflow: auto;
  }
</style>
