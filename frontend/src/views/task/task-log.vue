<template>
  <div class="task-log-wrapper" v-test="'taskLog'" v-bkloading="{ isLoading: loading }">
    <section class="log-side-nav" ref="sideContent">
      <div class="log-nav-select">
        <bk-input
          v-test="'hostSearch'"
          class="ip-filter-select"
          :placeholder="$t('IP模糊搜索')"
          v-model.trim="search"
          @change="handleSearch">
        </bk-input>
      </div>
      <div class="log-nav-wrapper"
           ref="logSide"
           v-bkloading="{ isLoading: !loading && listLoading }"
           @scroll="handleSideScroll">
        <div class="log-nav-head" :style="ghostStyle" v-if="virtualScroll"></div>
        <div class="log-nav-body auto-height" ref="content">
          <ul class="nav-list" v-test="'hostList'">
            <template v-for="item in renderNavData">
              <li
                :key="item.instanceId"
                :class="['nav-item', { 'item-active': curIp === item.innerIp + '' && item.instanceId === curId }]"
                :id="`${item.innerIp}-${item.instanceId}`"
                @click.stop="navHandle(item)">
                <div class="col-execution">
                  <loading-icon v-if="item.status === 'running'"></loading-icon>
                  <span v-else :class="`execut-mark execut-${ item.status }`"></span>
                  <span class="execut-text">{{ item.innerIp }}</span>
                </div>
              </li>
            </template>
          </ul>
          <bk-pagination
            small
            class="p10"
            :count.sync="pagination.count"
            :current.sync="pagination.current"
            :show-limit="false"
            :limit="pagination.limit"
            align="center"
            @change="handlePageChange" />
        </div>
      </div>
    </section>
    <section class="task-log-contaier" v-bkloading="{ isLoading: !loading && logLoading }">
      <div class="nodeman-navigation-content mb20">
        <span class="content-icon" @click="handleBack">
          <i class="nodeman-icon nc-back-left"></i>
        </span>
        <span class="content-header">{{ navTitle }}</span>
        <span class="content-subtitle">{{ titleRemarks }}</span>
      </div>
      <div class="log-operate">
        <bk-button
          class="retry-btn mr10 mb20"
          v-test="'retry'"
          v-if="showHostRetryBtn"
          :disabled="atomLoading || retryLoading"
          @click="handleRetry()">
          <loading-icon v-if="retryLoading"></loading-icon>
          <span v-else>{{ $t('整体重试') }}</span>
        </bk-button>
        <Tips class="tips mb20" show-close storage-key="__task_log_tips__">
          <template #default>
            <i18n path="任务日志topTip" class="task-log-tip">
              <i class="nodeman-icon nc-icon-bottom-fill"></i>
            </i18n>
          </template>
        </Tips>
      </div>
      <section class="task-log-content clearfix">
        <div class="step-wrapper">
          <div class="outer-border-cover">
            <bk-table
              ext-cls="log-step-table"
              ref="logStepTable"
              height="100%"
              size="small"
              :data="stepList"
              :row-style="getRowStyle"
              @row-click="handleStepClick">
              <bk-table-column :label="$t('步骤')" :resizable="false" min-width="180">
                <template #default="{ row, $index }">
                  <span :class="row.status" :title="row.step">
                    {{ `${ $index + 1 }. ${ row.step }` }}
                  </span>
                </template>
              </bk-table-column>
              <bk-table-column class-name="column-subscript" align="right" prop="spendTime" :label="$t('耗时')">
              </bk-table-column>
              <bk-table-column class-name="column-subscript" min-width="15"></bk-table-column>
              <bk-table-column class-name="column-subscript" :label="$t('执行情况')" :resizable="false" min-width="105">
                <template #default="{ row }">
                  <div
                    class="command-guide col-execution"
                    v-if="['running', 'pending'].includes(row.status) && showCommandBtn && row.step === commandStep">
                    <span class="execut-mark execut-ignored"></span>
                    <i18n tag="span" path="等待手动操作查看" class="execut-text">
                      <bk-button text theme="primary" @click="handleRowView">
                        {{ $t('操作指引') }}
                      </bk-button>
                    </i18n>
                  </div>
                  <div v-else class="col-execution">
                    <loading-icon v-if="row.status === 'running'"></loading-icon>
                    <span v-else :class="`execut-mark execut-${ row.status }`"></span>
                    <span :class="row.status" :title="statusMap[row.status]">{{ statusMap[row.status] }}</span>
                  </div>
                </template>
              </bk-table-column>
              <bk-table-column
                class-name="column-subscript"
                prop="opera"
                :width="hasOperaCell ? 100 : 30">
                <template #default="{ row, $index }">
                  <bk-button
                    v-if="row.status === 'running' && !(showCommandBtn && row.step === commandStep)"
                    v-test="'stop'"
                    ext-cls="step-operation"
                    size="small"
                    hover-theme="danger"
                    :disabled="stopLoading || retryLoading"
                    @click.stop="handleTaskStop(row)">
                    <loading-icon v-if="stopLoading"></loading-icon>
                    <span v-else>{{ $t('终止') }}</span>
                  </bk-button>
                  <i class="bk-icon icon-right-shape" v-if="isLogOverflow && scrollStep === $index"></i>
                </template>
              </bk-table-column>
            </bk-table>
          </div>
        </div>
        <div :class="['log-detail-wrapper', { 'log-detail-screen': isFullScreen }]">
          <div class="log-detail-content">
            <div class="log-header clearfix">
              <h4 class="title fl">{{ $t('执行日志') }}</h4>
              <div>
                <i class="mr20 nodeman-icon nc-xiazai"
                   v-bk-tooltips="{
                     delay: [300, 0],
                     content: $t('下载日志'),
                     theme: 'log-operate',
                     placements: ['top']
                   }"
                   v-test="'download'"
                   @click="exportHandle"></i>
                <i :class="`nodeman-icon nc-icon-${ isFullScreen ? 'un-' : '' }full-screen`"
                   v-bk-tooltips="{
                     delay: [300, 0],
                     content: isFullScreen ? $t('退出全屏') : $t('全屏'),
                     theme: 'log-operate',
                     placements: ['top']
                   }"
                   @click.stop="handleScreen"></i>
              </div>
            </div>
            <div class="log-body">
              <div class="log-sheet sheet-top"></div>
              <div class="log-content" ref="logContent">
                <div class="log-list" ref="logList">
                  <section v-for="(step, index) in stepList" :key="`step${index}`">
                    <div ref="step" :id="`log${index}`">
                      <template v-if="step.formatLog">
                        <div
                          v-for="(log, logIndex) in step.formatLog"
                          :key="logIndex"
                          :class="['log-item', log.type, { 'is-flod': log.isFlod }]">
                          <!-- eslint-disable-next-line vue/no-v-html -->
                          <span class="log-text" v-html="log.content"></span>
                          <i
                            v-if="log.type === 'debug'"
                            :class="`log-flod-icon bk-icon icon-play-shape ${ log.isFlod ? 'right' : 'down'}`"
                            @click="logTextToggle(log)">
                          </i>
                        </div>
                      </template>
                    </div>
                  </section>
                  <span class="dot" v-if="dotLoading">...</span>
                </div>
              </div>
              <div class="log-sheet sheet-bottom"></div>
            </div>
          </div>
          <div v-if="isLogOverflow && !isKeepScroll" class="btn-scroll-bottom" @click="scrollToBottom">
            <i class="nodeman-icon nc-icon-bottom-fill"></i>
          </div>
        </div>
      </section>
    </section>

    <TaskDetailSlider
      :task-id="taskId"
      :slider="slider"
      :table-list="navList"
      v-model="slider.show">
    </TaskDetailSlider>
  </div>
</template>

<script>
import { addListener, removeListener } from 'resize-detector';
import { TaskStore } from '@/store';
import pollMixin from '@/common/poll-mixin';
import Tips from '@/components/common/tips.vue';
import { downloadLog, debounce, isEmpty, takesTimeFormat, toHump } from '@/common/util';
import routerBackMixin from '@/common/router-back-mixin';
import TaskDetailSlider from './task-detail-slider.vue';

export default {
  name: 'TaskLog',
  components: {
    Tips,
    TaskDetailSlider,
  },
  mixins: [pollMixin, routerBackMixin],
  props: {
    hostInnerIp: {
      type: String,
      default: '',
    },
    instanceId: {
      type: String,
      default: '',
    },
    taskId: {
      type: [String, Number],
      default: '',
    },
    query: {
      type: Object,
      default: () => ({
        page: 1,
        pageSize: 50,
      }),
    },
  },
  data() {
    return {
      loading: true,
      logLoading: false, // 右下 - 日志loading
      stopLoading: false,
      retryLoading: false,
      atomLoading: false,
      dotLoading: false,
      reportLoading: false,
      hostTimer: null, // 主机状态轮询
      hostRuningQueue: [], // 执行状态主机队列
      needReport: true, // 是否需要上报日志
      jobType: '',
      jobTypeDisplay: '',
      cloudArea: '',
      tipsList: this.$t('任务日志topTip'),
      isFullScreen: false,
      logWrapperEle: null,
      isKeepScroll: true, // 日志是否保持在最新
      search: '',
      statusMap: {
        running: this.$t('正在执行'),
        failed: this.$t('执行失败'),
        part_failed: this.$t('部分失败'),
        success: this.$t('执行成功'),
        stop: this.$t('已终止'),
        pending: this.$t('等待执行'),
      },
      curIp: '',
      curId: -1,
      curCloudId: -1,
      isManualType: false,
      navList: [],
      needReloadLog: true, // 日志和列表同步加载优化
      stepList: [],
      // 组侧栏主机列表虚拟滚动相关参数
      startIndex: 0,
      endIndex: 0,
      height: 0,
      sideItemHeight: 40,
      handleSideScroll() {},
      reportRegExp: /End of collected logs/ig,
      scrollStep: 0,
      logOffsetTop: [],
      isManualTrigger: false, // 点击步骤时防止自动计算下标
      logContentHeight: 0, // 日志容器高度
      isLogOverflow: false, // 日志内容是否溢出
      pagination: {
        current: isNaN(this.query.page) ? 1 : Number(this.query.page),
        count: 0,
        limit: isNaN(this.query.pageSize) ? 50 : Number(this.query.pageSize),
      },
      listLoading: false,
      relativePosition: 0,
      movePosition: 0,
      slider: {
        show: false,
        isSingle: false,
        hostType: '',
        opType: '',
        row: {},
      },
    };
  },
  computed: {
    routetParent() {
      return TaskStore.routetParent;
    },
    navTitle() {
      return this.$t('执行日志标题', { ip: this.curIp, jobType: this.jobTypeDisplay });
    },
    titleRemarks() {
      return this.$t('所属云区域', { cloud: this.cloudArea });
    },
    // 初始化的时候可能带着成功或错误的筛选条件
    filterType() {
      return this.$route.query.type || '';
    },
    renderNavData() {
      if (this.navList && this.virtualScroll) {
        return this.navList.slice(this.startIndex, this.endIndex);
      }
      return this.navList || [];
    },
    setupNum() {
      return this.navList.length;
    },
    // 是否支持虚拟滚动
    virtualScroll() {
      return false; // 前端分页，无需虚拟滚动了
      // 44 : 表格一行的高度
      // return this.setupNum * 40 >= this.height
    },
    // 虚拟滚动高度
    scrollHeight() {
      // 156： footer和表头的高度
      return this.virtualScroll && this.height ? `${this.height - 72}px` : 'auto';
    },
    ghostStyle() {
      const allDataLength = this.navList ? this.navList.length : 0;
      return {
        height: `${allDataLength * this.sideItemHeight}px`,
      };
    },
    hasOperaCell() {
      return this.stepList.find(item => item.status === 'running');
      // return this.stepList.find(item => item.status === 'running' || item.status === 'failed')
    },
    showHostRetryBtn() {
      return this.stepList.some(item => item.status === 'failed');
    },
    // 操作的主机或任务类型 Agent | Proxy | Plugin
    operateHost() {
      const res = /(agent)|(proxy)|(plugin)/ig.exec(this.jobType);
      return res ? res[0] : '';
    },
    searchIpList() {
      const data = this.search.replace(/;+|；+|_+|\\+|，+|,+|、+|\s+/g, ',').replace(/,+/g, ',')
        .split(',');
      return [...new Set(data.filter(item => !!item))];
    },
    // 能查看命令的任务类型
    showCommandBtn() {
      if (!this.operateHost || this.operateHost === 'Plugin' || !this.isManualType) {
        return false;
      }
      return /(INSTALL)|(REINSTALL)|(UPGRADE)/ig.test(this.jobType);
    },
    commandStep() {
      return /UN/ig.test(this.jobType) ? this.$t('手动卸载Guide') : this.$t('手动安装Guide');
    },
  },
  watch: {
    needReloadLog(val) {
      if (val) {
        this.getLogDetail();
      }
    },
    hostRuningQueue(val) {
      if (val && val.length > 0 && !this.hostTimer) {
        this.handleHostRunTimer();
      } else if (!val || val.length === 0) {
        clearTimeout(this.hostTimer);
        this.hostTimer = null;
      }
    },
  },
  created() {
    // this.handleSideScroll = throttle(this.rootScroll, 0)
    this.handleSearch = debounce(300, this.handleSearchIp);
    this.curId = this.instanceId;
    this.getLogDetail();
  },
  mounted() {
    this.height = this.$refs.sideContent.clientHeight;
    this.getHostList('init');
    this.scrollWatch();
    this.listenResize = debounce(300, v => this.handleResize(v));
    addListener(this.$el, this.listenResize);
  },
  beforeDestroy() {
    removeListener(this.$el, this.listenResize);
    window.removeEventListener('scroll', this.handleScroll);
    clearTimeout(this.hostTimer);
    this.hostTimer = null;
    this.hostRuningQueue = [];
  },
  methods: {
    /**
     * 拉取左侧任务下的主机列表
     */
    async getHostList(type) {
      const { limit = 50, current = 1 } = this.pagination;
      const params = {
        canceled: true,
        jobId: this.taskId,
        params: {
          pagesize: Number(limit),
          page: Number(current),
          conditions: [
            {
              key: 'ip',
              value: this.searchIpList,
            },
          ],
        },
      };
      this.listLoading = true;
      const res = await TaskStore.requestHistoryTaskDetail(params);
      if (res.canceled) return; // 多次调用搜索时会中断loading状态
      if (res) {
        const { list: data, status, total = 0, jobType = '', jobTypeDisplay = '' } = res;
        this.pagination.count = total;
        this.jobType = toHump((jobType || '').toLowerCase());
        this.jobTypeDisplay = jobTypeDisplay;
        this.isManualType = data.some(item => item.isManual);
        const list = data.filter(item => item.instanceId && item.status !== 'filtered');
        this.navList = list;
        this.hostRuningQueue = /running/ig.test(status) ? [1] : [];
        // 判断实例是否存在当前列表中，不存在则重新查询
        const propHost = list.find(item => (this.hostInnerIp && item.innerIp === this.hostInnerIp)
          || (`${item.instanceId}` === this.instanceId)) || (type === 'init' && await this.getCurrentHost());

        if (propHost) {
          this.curIp = propHost.innerIp || '';
          this.cloudArea = propHost.bkCloudName || '';
        } else {
          this.navHandle(res.list[0]);
        }
      }
      this.scrollItemIntoView();
      this.listLoading = false;
    },
    // 获取当前主机信息（由于分页原因，调转过来的主机可能不在当前页）
    async getCurrentHost() {
      // 忽略的主机没有instance_id，只有innerIp
      const params = {
        jobId: this.taskId,
        params: {
          pagesize: -1,
          conditions: this.hostInnerIp
            ? [{ key: 'ip', value: this.hostInnerIp }]
            : [{ key: 'instance_id', value: this.instanceId }],
        },
      };
      const res = await TaskStore.requestHistoryTaskDetail(params);
      if (res?.list) {
        const [firstItem] = res.list;
        // 往当前列中插入当前主机信息
        this.navList.unshift(firstItem);
        return firstItem;
      }

      return null;
    },
    // 滚动列表到可视区域
    scrollItemIntoView() {
      this.$nextTick(() => {
        const ele = document.querySelector(`li[id="${this.curIp}-${this.curId}"]`);
        ele?.scrollIntoView();
      });
    },
    navHandle(item) {
      this.curId = `${item.instanceId}`;
      if (this.instanceId === this.curId) {
        return false;
      }
      this.needReport = true;
      this.curIp = item.innerIp || '';
      this.cloudArea = item.bkCloudName || '';
      this.$router.replace({
        name: 'taskLog',
        params: {
          type: this.taskType,
          instanceId: `${item.instanceId}`,
        },
        query: {
          page: this.pagination.current || 1,
          pageSize: this.pagination.limit || 50,
        },
      });
      this.needReloadLog = true;
    },
    filterIpHandle() {
      if (this.search) {
        let ipArr = this.search.replace(/;+|；+|_+|\\+|，+|,+|、+|\s+/g, ',').replace(/,+/g, ',')
          .split(',');
        ipArr = [...new Set(ipArr.filter(item => !!item))];
        const navList = this.navList.reduce((arr, item) => {
          if (ipArr.some(ip => item.innerIp.indexOf(ip) !== -1)) {
            arr.push(item);
          }
          return arr;
        }, []);
        this.navList.splice(0, this.setupNum, ...navList);
        this.$refs.content.style.transform = 'translate3d(0, 0, 0)';
      } else {
        this.navList.splice(0, this.setupNum, ...this.navList);
        this.$nextTick(() => {
          this.$refs.logSide.scrollTop = this.startIndex * this.sideItemHeight;
        });
      }
    },
    /**
     * 主机日志详情
     */
    async getLogDetail() {
      if (!this.needReloadLog) {
        return;
      }
      this.logLoading = true;
      const { curId } = this; // 多次切换路由会变化
      const res = await TaskStore.requestHistoryHostLog({
        jobId: this.taskId,
        params: {
          instance_id: this.curId,
        },
      });
      if (res && curId === this.curId) {
        this.resultHandle(res);
      }
      this.needReloadLog = false;
      this.logLoading = false;
      this.loading = false;
    },
    /**
     * 处理轮询的数据
     */
    async handlePollData() {
      const res = await TaskStore.requestHistoryHostLog({
        jobId: this.taskId,
        params: {
          instance_id: this.curId,
        },
      });
      if (res && !this.stopLoading) {
        this.resultHandle(res);
      }
    },
    /**
     * 单主机终止任务
     */
    async handleTaskStop(row) {
      this.stopLoading = true;
      this.runingQueue = [];
      const res = await TaskStore.requestTaskStop({
        jobId: this.taskId,
        params: { instance_id_list: [this.instanceId] },
      });
      if (res.result) {
        row.status = 'stop';
        this.dotLoading = false;
        this.runingQueue = [-1];
        this.requestReport();
      }
      this.stopLoading = false;
    },
    /**
     * 原子任务重试
     */
    async handleRetry(row) {
      const loadingKey = row ? 'atomLoading' : 'retryLoading';
      const requireyKey = row ? 'requestNodeRetry' : 'requestTaskRetry';
      this[loadingKey] = true;
      const res = await TaskStore[requireyKey]({
        jobId: this.taskId,
        params: row ? { instance_id: this.instanceId } : { instance_id_list: [this.instanceId] },
      });
      if (res.result) {
        if (row) {
          row.status = 'running';
        }
        this.runingQueue = [-1];
        this.hostRuningQueue = [1];
        this.navList.forEach((item) => {
          if (item.instanceId === this.instanceId) {
            item.status = 'running';
          }
        });
        this.navList.forEach((item) => {
          if (item.instanceId === this.instanceId) {
            item.status = 'running';
          }
        });
      }
      this[loadingKey] = false;
    },
    /**
     * 日志上报
     */
    async requestReport() {
      this.reportLoading = true;
      await TaskStore.requestReportLog({
        jobId: this.taskId,
        params: { instance_id: this.instanceId },
      });
      this.needReport = false; // 不论请求成功失败，只发一次
      this.reportLoading = false;
    },
    resultHandle(res) {
      res.forEach((item, index) => {
        item.id = index;
        item.formatLog = this.formatLog(item.log);
        item.spendTime = this.stepSpendTime(item.start_time, item.finish_time);
      });
      this.stepList.splice(0, this.stepList.length, ...res);
      const len = res.length;
      const isSuccess = len && res[len - 1].status === 'success';
      const isFailed = res.some(item => item.status === 'failed' || item.status === 'stop');
      this.dotLoading = res.some(item => item.status === 'running');
      const hasReportRes = res.find(item => this.reportRegExp.test(item.log)); // 日志中是否存在结束日志上报完成标识
      const needReport = isFailed && !hasReportRes;
      // 成功或在已经获取采集日志并失败的情况下无需刷新日志（插件没有采集日志）
      if (this.operateHost !== 'Plugin') {
        this.runingQueue = isSuccess || (isFailed && hasReportRes)
          ? [] : [-1]; // 非执行成功 或 失败且包含上报成功语句 一直轮询
      } else {
        this.runingQueue = isSuccess || isFailed ? [] : [-1];
      }
      if (this.operateHost && this.operateHost !== 'Plugin' && needReport && this.needReport && !this.reportLoading) {
        this.requestReport();
      }
      if (this.isKeepScroll) {
        this.$nextTick(() => {
          this.scrollToBottom();
        });
      }
      this.$nextTick(() => {
        this.logOffsetTop = this.$refs.step ? this.$refs.step.map(item => ({
          top: item.offsetTop,
          height: item.offsetHeight,
          content: !!item.textContent,
        })) : [];
        this.handleResize();
      });
    },
    // 格式化日志
    formatLog(log) {
      if (!log) {
        return null;
      }
      // 提取 debug 日志
      const debugLog = log.match(/\[((?!\[).)*DEBUG\] \*+ Begin of collected logs[\s\S]*End of collected logs \*+/ig);
      // eslint-disable-next-line vue/max-len
      const copyLog = log.replace(/\[((?!\[).)*DEBUG\] \*+ Begin of collected logs[\s\S]*End of collected logs \*+/ig, '**__DEBUG__**');
      // 换行符 切分日志
      const logSplit = copyLog.split('\n');
      const logList = logSplit.map((item) => {
        if (/\*\*__DEBUG__\*\*/g.test(item)) {
          return {
            type: 'debug',
            content: item.replace(/\*\*__DEBUG__\*\*/g, debugLog.shift()), // 回填 debug 日志
            isFlod: true,
          };
        }
        return {
          type: /\[((?!\[).)*ERROR\]/ig.test(item) ? 'error' : 'info',
          content: item,
          isFlod: false,
        };
      });
      return logList;
    },
    scrollWatch() {
      this.logWrapperEle = this.$refs.logContent;
      this.logWrapperEle.addEventListener('scroll', this.handleScroll);
    },
    handleScroll() {
      const { scrollTop } = this.logWrapperEle;
      // 保留本次滚动scrollTop（和上次进行对比，判断滚动方向）
      this.movePosition = scrollTop;
      const contentHeight = this.logWrapperEle.scrollHeight;
      this.isKeepScroll = scrollTop >= contentHeight - this.logContentHeight;

      if (!this.isManualTrigger) {
        const paddingTop = 20;
        // 判断滚动方向
        const direction = this.movePosition < this.relativePosition ? 'up' : 'down';
        let index = 0;

        if (direction === 'up') {
          // 向上滚动时找到第一个即可
          index = this.logOffsetTop.findIndex(item => item.content
            && ((scrollTop + paddingTop) < (item.top + item.height)));
        } else {
          // 向下滚动时找到最后一个
          this.logOffsetTop.forEach((item, logIndex) => {
            if (item.content && (scrollTop + this.logContentHeight > item.top + paddingTop)) {
              index = logIndex;
            }
          });
        }

        if (index < 0) {
          index = this.logOffsetTop.findIndex(item => item.content);
          this.logOffsetTop.forEach((item, itemIndex) => {
            if (item.content) {
              index = itemIndex;
            }
          });
        }
        this.scrollStep = index;
        // 更新上一次的 scrollTop
        this.relativePosition = this.movePosition;
      }
      this.isManualTrigger = false;
    },
    /*
      * 滚动到底部
      */
    scrollToBottom() {
      this.isKeepScroll = true;
      const contentHeight = this.logWrapperEle.scrollHeight;
      this.logWrapperEle.scrollTop = contentHeight - this.logContentHeight;
    },
    /**
     * 日志步骤点击事件
     */
    handleStepClick(row) {
      if (!row.status) return;
      this.isManualTrigger = true; // 打开手动计算模式
      // 找到锚点
      const rowIndex = this.stepList.findIndex(item => item.id === row.id && item.step === row.step);
      const anchor = document.getElementById(`log${rowIndex}`);
      if (anchor && this.logWrapperEle) {
        if (row.status === 'running' || row.status === 'pending') {
          this.isManualTrigger = false;
          this.scrollToBottom();
        } else {
          this.scrollStep = rowIndex;
          const total = anchor.offsetTop; // 定位锚点
          this.logWrapperEle.scrollTop = total - 20; // 20 顶部遮罩层高度 -> log-header
        }
      }
    },
    /*
    * 虚拟滚动
    */
    rootScroll() {
      if (!this.virtualScroll) return;

      if (this.navList.length) {
        this.updateRenderData(this.$refs.logSide.scrollTop);
      }
    },
    updateRenderData(scrollTop = 0) {
      const count = Math.ceil((this.$refs.logSide.clientHeight) / this.sideItemHeight);
      // 滚动后可视区新的 startIndex
      const newStartIndex = Math.floor(scrollTop / this.sideItemHeight);
      // 滚动后可视区新的 endIndex
      const newEndIndex = newStartIndex + count;
      this.startIndex = newStartIndex;
      this.endIndex = newEndIndex;
      this.$refs.content.style.transform = `translate3d(0, ${newStartIndex * this.sideItemHeight}px, 0)`;
    },
    /**
     * 返回
     */
    handleBack() {
      this.routerBack();
    },
    /**
     * 下载日志
     */
    exportHandle() {
      const logArr = this.stepList.reduce((arr, item) => {
        arr.push(item.log);
        return arr;
      }, []);
      downloadLog(`bk_nodeman_${this.taskId}_${this.curIp}.log`, logArr.join('\n'));
    },
    /**
     * 日志全屏
     */
    handleScreen() {
      this.isFullScreen = !this.isFullScreen;
      this.$nextTick(() => {
        this.handleResize();
      });
    },
    getRowStyle() {
      return {
        cursor: this.isLogOverflow ? 'pointer' : 'default',
      };
    },
    /**
     * 折叠日志
     */
    logTextToggle(log) {
      if (log.type === 'debug') {
        log.isFlod = !log.isFlod;
        this.$nextTick(() => {
          this.logOffsetTop = this.$refs.step ? this.$refs.step.map(item => ({
            top: item.offsetTop,
            content: !!item.textContent,
          })) : [];
        });
      }
    },
    /**
     * 监听窗口大小，判断是否需要展示日志步骤下标
     */
    handleResize() {
      this.logContentHeight = this.logWrapperEle.offsetHeight;
      this.isLogOverflow = this.$refs.logList && (this.logContentHeight < this.$refs.logList.offsetHeight);
    },
    /**
     * 步骤耗时
     */
    stepSpendTime(startTime, endTime) {
      if (isEmpty(startTime) || isEmpty(endTime)) return '';
      const start = new Date(startTime);
      const end = new Date(endTime);
      if (/Invalid Date/.test(start) || /Invalid Date/.test(end)) return '';
      return takesTimeFormat((end - start) / 1000);
    },
    // 主机任务执行状态轮询
    handleHostRunTimer() {
      const fn = async () => {
        if (this.hostRuningQueue.length === 0) {
          clearTimeout(this.hostTimer);
          this.hostTimer = null;
          return;
        }
        const params = {
          jobId: this.taskId,
          params: { pagesize: -1 },
        };
        const res = await TaskStore.requestHistoryTaskDetail(params);
        if (res) {
          const { list: data, status } = res;
          const list = data.filter(item => item.instanceId && item.status !== 'filtered');
          this.isManualType = list.some(item => item.isManual);
          const hostStatusMap = list.reduce((obj, item) => {
            obj[item.bkHostId] = item.status;
            return obj;
          }, {});
          this.hostRuningQueue = /running/ig.test(status) ? [1] : [];
          this.navList.forEach((item) => {
            item.status = hostStatusMap[item.bkHostId] || item.status;
          });
          this.navList.forEach((item) => {
            item.status = hostStatusMap[item.bkHostId] || item.status;
          });
        }
        this.hostTimer = setTimeout(() => {
          fn();
        }, this.interval);
      };
      this.hostTimer = setTimeout(fn, this.interval);
    },
    // 分页
    handlePageChange() {
      this.getHostList();
    },
    handleSearchIp() {
      this.pagination.count = 0;
      this.pagination.current = 1;
      this.getHostList();
    },
    handleRowView() {
      const curHost = this.navList.find(item => item.instanceId === this.instanceId);
      if (!!curHost) {
        if (this.operateHost === 'Proxy') {
          this.slider.hostType = this.operateHost;
        } else {
          this.slider.hostType = curHost.bkCloudId === window.PROJECT_CONFIG.DEFAULT_CLOUD ? 'Agent' : 'Pagent';
        }
        this.slider.opType = curHost.opTypeDisplay;
        this.slider.isSingle = true;
        this.slider.row = curHost;
        this.slider.show = true;
      }
    },
  },
};
</script>

<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";
@import "@/css/variable.css";
@import "@/css/transition.css";

$headerColor: #313238;

/** 组件顶部导航样式 */
.nodeman-navigation-content {
  position: relative;
  padding-left: 22px;
  height: 20px;
  line-height: 20px;

  @mixin layout-flex row, baseline;
  .content-icon {
    position: absolute;
    height: 20px;
    top: -4px;
    left: 0;
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
    margin-left: 8px;
    font-size: 12px;
    color: #979ba5;
  }
}
.task-log-wrapper {
  display: flex;
  height: calc(100vh - 52px);
  .log-side-nav {
    width: 240px;
    height: 100%;
    border-right: 1px solid #dcdee5;
    background: #fafbfd;
  }
  .log-nav-wrapper {
    position: relative;
    height: calc(100% - 72px);
    overflow: auto;
    &::-webkit-scrollbar-thumb {
      box-shadow: inset 0 0 8px 8px #c4c6cc;
    }
  }
  .log-nav-head {
    position: relative;
    height: 100%;
  }
  .log-nav-body {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    &.auto-height {
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
  }
  .nav-list {
    height: 100%;
    overflow-y: auto;
  }
  .nav-item {
    display: flex;
    align-items: center;
    padding-left: 20px;
    width: 100%;
    height: 40px;
    line-height: 40px;
    font-size: 14px;
    color: #63656e;
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    cursor: pointer;
    &:hover {
      background: #f0f1f5;
    }
    &.item-active {
      color: #63656e;
      background: #e1ecff;
    }
  }
  .log-nav-select {
    padding: 20px;
  }
  .log-operate {
    display: flex;
    justify-content: space-between;
    .retry-btn {
      min-width: 86px;
    }
    .tips {
      flex: 1;
    }
  }
  .task-log-tip {
    line-height: 16px;
    i {
      font-size: 14px;
    }
  }
  .task-log-contaier {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px 24px 20px 24px;
    overflow: auto;
  }
  .task-log-content {
    flex: 1;
    display: flex;
    height: calc(100% - 100px);
  }
  .step-wrapper {
    width: 420px;
    min-width: 40%;
    height: 100%;
    border-bottom: 0;
    background: #fafbfd;
    overflow: hidden;
  }
  .outer-border-cover {
    height: 100%
  }
  .log-step-table {
    width: 100%;
    .pending {
      color: #c4c6cc;
    }
    .step-operation {
      padding: 0 5px;
      min-width: 54px;
    }
    >>> .column-subscript {
      .cell {
        padding: 0 10px;
      }
      i.icon-right-shape {
        position: absolute;
        top: 15px;
        right: 10px;
        color: #c4c6cc;
      }
    }
    .command-guide {
      position: absolute;
      top: 10px;
      left: 10px;
      white-space: nowrap;
      z-index: 5;
    }
  }
  .log-detail-wrapper {
    position: relative;
    flex: 1;
    padding-left: 10px;
    overflow: hidden;
    &.log-detail-screen {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      left: 0;
      padding: 0;
      z-index: 1050;
    }
    .btn-scroll-bottom {
      position: absolute;
      right: 24px;
      bottom: 10px;
      font-size: 0;
      cursor: pointer;
      z-index: 20;
      i {
        font-size: 28px;
        color: #98989b;
      }
    }
  }
  .log-detail-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    border-radius: 0px 0px 2px 2px;
    background: #313238;
  }
  .log-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 15px 0 20px;
    height: 43px;
    border-bottom: 1px solid #3b3c42;
    font-size: 14px;
    background: #202024;
    overflow: hidden;
    .title {
      flex: 1;
      margin: 0;
      font-weight: normal;
      color: #fff;
    }
    .nodeman-icon {
      font-size: 16px;
      color: #979ba5;
      cursor: pointer;
    }
  }
  .log-body {
    flex: 1;
    position: relative;
    width: 100%;
    overflow: hidden;
    .log-sheet {
      position: absolute;
      left: 0;
      right: 14px;
      height: 20px;
      background: #313238;
      z-index: 10;
    }
    .sheet-top {
      top: 0;
    }
    .sheet-bottom {
      bottom: 0;
    }
  }
  .log-content {
    width: 100%;
    height: 100%;
    overflow: auto;
    &::-webkit-scrollbar {
      width: 14px;
      height: 16px;
    }
    &::-webkit-scrollbar-thumb {
      border-radius: 0;
      border: 1px solid #63656e;
      background: #3b3c42;
      box-shadow: none;
    }
    &::-webkit-scrollbar-track {
      box-shadow: inset 1px 0 1px #3b3c42;
      background-color: #313238;
    }
    .log-list {
      padding: 20px 0 20px 0;
    }
    .log-item {
      position: relative;
      padding-left: 30px;
      padding-right: 28px;
      .log-flod-icon {
        position: absolute;
        top: 10px;
        left: 4px;
        padding: 4px 4px;
        font-size: 12px;
        color: #c4c6cc;
        cursor: pointer;
        transition: transform .2s ease-in-out;
        &.down {
          transform: rotate(90deg);
        }
      }
      .log-text {
        display: inline-block; /* stylelint-disable-next-line declaration-no-important */
        font-family: "Monaco", "Menlo", "Ubuntu Mono", "Consolas", "source-code-pro", "monospace" !important;
        line-height: 24px;
        font-size: 12px;
        color: #c4c6cc;
        white-space: pre-wrap;
        word-wrap: break-word;
        word-break: break-word;
        >>> a {
          color: #3c96ff;
          text-decoration: underline;
        }
      }
      &.error .log-text {
        color: #cc4141;
      }
      &.debug {
        padding-top: 7px;
        padding-bottom: 7px;
        background: #2a2b2f;
        .log-text:first-line {
          color: #f0f1f5;
          font-weight: 700;
        }
      }
      &.is-flod .log-text {
        height: 24px;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
}
/deep/ .bk-dialog-body {
  padding: 0;
}
.dot {
  position: relative;
  display: inline-block;
  margin-left: 30px;
  font-size: 20px;
  line-height: 22px;
  vertical-align: bottom;
  color: transparent;
  overflow: hidden; /* stylelint-disable-next-line declaration-no-important */
  font-family: simsun!important;
  &::after {
    position: absolute;
    left: 0;
    top: 0;
    display: inline-block;
    content: "...";
    width: 0;
    height: 100%;
    z-index: 5;
    color: #c4b9b9; /* stylelint-disable-next-line declaration-no-important */
    font-family: "simsun"!important;
    vertical-align: bottom;
    overflow: hidden;
    animation: dot 3s infinite step-start;
  }
}
</style>
