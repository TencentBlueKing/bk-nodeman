<template>
  <div :class="['plugin-steps', { 'footer-fixed': isScroll && table.data.length }]">
    <!--agent操作-->
    <section class="agent-operate mb15">
      <!--agent操作-->
      <div class="agent-operate-left">
        <!--选择业务-->
        <bk-biz-select
          v-model="search.biz"
          ext-cls="left-select"
          :placeholder="$t('全部业务')"
          @change="handleBizChange">
        </bk-biz-select>
        <bk-select
          class="plugin-select ml10"
          v-model="search.osType"
          :popover-options="{ 'boundary': 'window' }"
          :clearable="false"
          @selected="handleBizChange">
          <bk-option v-for="option in osTypeList"
                     :key="option.id"
                     :id="option.id"
                     :name="option.name">
          </bk-option>
        </bk-select>
      </div>
      <!--agent搜索-->
      <div class="agent-operate-right">
        <bk-search-select
          ref="searchSelect"
          ext-cls="right-select"
          :data="searchSelectData"
          v-model="searchSelectValue"
          :show-condition="false"
          :placeholder="$t('agent列表搜索')"
          @paste.native.capture.prevent="handlePaste"
          @change="handleSearchSelectChange">
        </bk-search-select>
      </div>
    </section>
    <!--agent列表-->
    <section class="agent-content" v-bkloading="{ isLoading: loading }">
      <bk-table
        ref="hostTable"
        :class="`head-customize-table ${ fontSize }`"
        :data="table.data"
        :cell-class-name="handleCellClass"
        :span-method="colspanHandle"
        :row-style="getRowStyle"
        @row-click="toggleExpansion">
        <template #prepend>
          <transition name="tips">
            <div class="selection-tips" v-show="isAllChecked && selectionCount">
              <div v-if="!disabledAllChecked">
                {{ $t('已选') }}
                <span class="tips-num">{{ selectionCount }}</span>
                {{ $t('条') }},
              </div>
              <div v-if="!disabledAllChecked && !isSelectedAllPages">
                {{ $t('共') }}
                <span class="tips-num">{{ table.pagination.count }}</span>
                {{ $t('条') }}
              </div>
              <bk-button ext-cls="tips-btn" text v-else @click="handleClearSelection">{{ $t('取消选择所有数据') }}</bk-button>
            </div>
          </transition>
        </template>
        <bk-table-column type="expand" width="30" align="center">
          <template #default="{ row }">
            <section class="host-plugin expand-row clearfix">
              <template v-if="Array.isArray(row.plugin_status) && row.plugin_status.length">
                <div class="host-plugin-item" v-for="plug in row.plugin_status" :key="plug.name">
                  <div class="col-status" v-if="plug">
                    <span class="plugin-name">{{ plug.name }}：</span>
                    <span :class="'status-mark status-' + plug.status.toLowerCase()"></span>
                    <span class="plugin-version">{{ plug.version | filterEmpty }}</span>
                  </div>
                </div>
              </template>
              <p class="tc" v-else>{{ $t('暂无其他插件信息') }}</p>
            </section>
          </template>
        </bk-table-column>
        <bk-table-column
          key="selection"
          width="70"
          align="left"
          :resizable="false"
          :render-header="renderSelectionHeader">
          <template #default="{ row }">
            <auth-component
              class="inline-block"
              tag="div"
              :authorized="row.operate_permission"
              :apply-info="[{
                action: 'plugin_operate',
                instance_id: row.bk_biz_id,
                instance_name: row.bk_biz_name
              }]"
              @click="stopBubble">
              <template slot-scope="{ disabled }">
                <bk-checkbox
                  :value="row.selection"
                  :disabled="row.status !== 'running' || disabled"
                  @change="handleRowCheck(arguments, row)">
                </bk-checkbox>
              </template>
            </auth-component>
          </template>
        </bk-table-column>
        <bk-table-column class-name="row-ip" min-width="50" :label="$t('节点类型')" prop="node_type" resizable>
          <template #default="{ row }">
            <span>{{ row.node_type ? osType[row.node_type] : '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          key="IP"
          label="IP"
          prop="inner_ip"
          resizable>
          <template #default="{ row }">
            <div v-bk-overflow-tips>{{ row.inner_ip }}</div>
          </template>
        </bk-table-column>
        <bk-table-column
          key="biz"
          :label="$t('归属业务')"
          prop="bk_biz_name"
          resizable
          v-if="filter['bk_biz_name'].mockChecked">
          <template #default="{ row }">
            <div v-bk-overflow-tips>{{ row.bk_biz_name }}</div>
          </template>
        </bk-table-column>
        <bk-table-column
          key="cloudArea"
          :label="$t('云区域')"
          :render-header="renderFilterHeader"
          prop="bk_cloud_id"
          resizable
          v-if="filter['bk_cloud_id'].mockChecked">
          <template #default="{ row }">
            <span v-if="row.bk_cloud_name">{{ row.bk_cloud_name }}</span>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <bk-table-column
          key="system"
          :label="$t('操作系统')"
          prop="os_type"
          resizable
          :render-header="renderFilterHeader"
          v-if="filter['os_type'].mockChecked">
          <template #default="{ row }">
            {{ osMap[row.os_type] | filterEmpty }}
          </template>
        </bk-table-column>
        <bk-table-column
          key="status"
          :label="$t('Agent状态')"
          prop="status"
          :render-header="renderFilterHeader"
          resizable
          v-if="filter['agent_status'].mockChecked">
          <template #default="{ row }">
            <div class="col-status" v-if="row.status_display">
              <span :class="'status-mark status-' + row.status"></span>
              <span>{{ row.status_display }}</span>
            </div>
            <div class="col-status" v-else>
              <span class="status-mark status-unknown"></span>
              <span>{{ row.status_display }}</span>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          key="version"
          :label="$t('Agent版本')"
          prop="version"
          :render-header="renderFilterHeader"
          resizable
          v-if="filter['agent_version'].mockChecked">
          <template #default="{ row }">
            <span>{{ row.version | filterEmpty }}</span>
          </template>
        </bk-table-column>
        <template v-for="(plugin, index) in pluginList">
          <bk-table-column
            :key="index"
            :label="plugin"
            :prop="plugin"
            :render-header="renderFilterHeader"
            resizable>
            <template #default="{ row }">
              <div class="col-status" v-if="statusMap[row[`${plugin}Status`]]">
                <span :class="'status-mark status-' + row[`${plugin}Status`]"></span>
                <span>{{ row[`${plugin}Version`] }}</span>
              </div>
              <div class="col-status" v-else>
                <span class="status-mark status-unknown"></span>
                <span>{{ row[`${plugin}Version`] }}</span>
              </div>
            </template>
          </bk-table-column>
        </template>
        <!--自定义字段显示列-->
        <bk-table-column
          key="setting"
          prop="colspaSetting"
          :render-header="renderHeader"
          width="42"
          :resizable="false">
        </bk-table-column>
      </bk-table>
      <bk-pagination
        ext-cls="pagination"
        size="small"
        :limit="table.pagination.limit"
        :count="table.pagination.count"
        :current="table.pagination.current"
        :limit-list="table.pagination.limitList"
        align="right"
        show-total-count
        show-selection-count
        :selection-count="selectionCount"
        @change="handlePageChange"
        @limit-change="handlePageLimitChange">
      </bk-pagination>
      <div class="bk-plugin-button" v-if="!loading">
        <bk-popover placement="right"
                    :disabled="disabledTip"
                    :content="$t('无可操作的主机')">
          <bk-button theme="primary"
                     :disabled="!isNextStep"
                     @click="stepHandle">
            {{ $t('下一步') }}
          </bk-button>
        </bk-popover>
      </div>
    </section>
  </div>
</template>
<script>
import { MainStore, PluginOldStore } from '@/store/index';
import ColumnCheck from '@/views/agent/components/column-check';
import tableHeaderMixins from '@/components/common/table-header-mixins';
import pollMixin from '@/common/poll-mixin';
import { debounce, isEmpty } from '@/common/util';
import ColumnSetting from '@/components/common/column-setting';
import { addListener, removeListener } from 'resize-detector';
import { bus } from '@/common/bus';

export default {
  name: 'StepSelectHost',
  mixins: [tableHeaderMixins, pollMixin],
  props: {
    ipInfo: {
      type: Object,
      default() {
        return {
          ip: '',
          cloud_id: '',
        };
      },
    },
  },
  data() {
    return {
      table: {
        // 列表数据
        data: [],
        // 分页
        pagination: {
          current: 1,
          count: 0,
          limit: 50,
          limitList: [50, 100, 200],
        },
      },
      checkedCount: 0, // 跨页全选拉取数量
      loading: false,
      checkLoading: false, // 跨页全选loading
      selectionRow: [],
      // 监听界面滚动
      listenResize: null,
      isScroll: false,
      // 列表字段显示配置
      filter: {
        inner_ip: {
          checked: true,
          disabled: true,
          mockChecked: true,
          name: 'IP',
          id: 'inner_ip',
        },
        agent_version: {
          checked: true,
          disabled: false,
          mockChecked: true,
          name: this.$t('Agent版本'),
          id: 'agent_version',
        },
        agent_status: {
          checked: true,
          disabled: true,
          mockChecked: true,
          name: this.$t('Agent状态'),
          id: 'agent_status',
        },
        bk_cloud_id: {
          checked: true,
          mockChecked: true,
          disabled: false,
          name: this.$t('云区域'),
          id: 'bk_cloud_id',
        },
        bk_biz_name: {
          checked: true,
          disabled: false,
          mockChecked: true,
          name: this.$t('业务'),
          id: 'bk_biz_name',
        },
        topology: {
          checked: false,
          disabled: false,
          mockChecked: false,
          name: this.$t('业务拓扑'),
          id: 'topology',
        },
        os_type: {
          checked: true,
          disabled: false,
          mockChecked: true,
          name: this.$t('操作系统'),
          id: 'os_type',
        },
        node_from: {
          checked: false,
          disabled: false,
          mockChecked: false,
          name: this.$t('节点来源'),
          id: 'node_from',
        },
      },
      // 状态map
      statusMap: {
        running: this.$t('正常'),
        terminated: this.$t('异常'),
        unknown: this.$t('未知'),
        unregister: this.$t('未知'),
      },
      osMap: {
        LINUX: 'Linux',
        WINDOWS: 'Windows',
        AIX: 'AIX',
      },
      osType: {
        AGENT: 'Agent',
        PROXY: 'Proxy',
        PAGENT: 'P-Agent',
      },
      // 常用插件map
      pluginList: ['basereport', 'processbeat', 'exceptionbeat', 'bkunifylogbeat', 'bkmonitorbeat'],
      // 搜索相关
      search: {
        biz: [],
        osType: '',
      },
      osTypeList: [],
      // 搜索防抖
      initAgentListDebounce() {},
      // 是否是跨页全选
      isSelectedAllPages: false,
      // 标记删除数组
      markDeleteArr: [],
      ipRegx: new RegExp('^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$'),
      operateBiz: [],
    };
  },
  computed: {
    permissionSwitch() {
      return MainStore.permissionSwitch;
    },
    bkBizList() {
      return MainStore.bkBizList;
    },
    selectedBiz() {
      return MainStore.selectedBiz;
    },
    fontSize() {
      return MainStore.fontSize;
    },
    // 当前列表选择数据
    selection() {
      return this.table.data.filter(item => item.status === 'running' && item.selection);
    },
    // 当前是否是半选状态
    indeterminate() {
      if (this.isSelectedAllPages) {
        return !!this.markDeleteArr.length && this.markDeleteArr.length !== this.table.pagination.count;
      }
      return !this.table.data.every(item => item.job_result.status === 'RUNNING'
          || item.selection
          || (this.permissionSwitch ? !item.operate_permission : false))
        && !this.table.data.every(item => item.job_result.status === 'RUNNING'
          || !item.selection
          || (this.permissionSwitch ? !item.operate_permission : false));
    },
    // 是否全选
    isAllChecked() {
      if (this.isSelectedAllPages) {
        return !this.markDeleteArr.length;
      }
      return !!this.table.data.filter(item => item.status === 'running'
        && (this.permissionSwitch ? item.operate_permission : true)).length
        && this.table.data.every(item => item.status !== 'running'
                        || item.selection
                        || (this.permissionSwitch ? !item.operate_permission : false));
    },
    // 是否禁用全选checkbox
    disabledCheckBox() {
      return this.table.data.every(item => item.status !== 'running'
                    || (this.permissionSwitch ? !item.operate_permission : false));
    },
    // 是否禁用跨页全选
    disabledAllChecked() {
      return this.table.pagination.count <= this.table.pagination.limit;
    },
    // 已勾选条数
    selectionCount() {
      if (this.isSelectedAllPages) {
        return this.checkedCount ? this.checkedCount - this.markDeleteArr.length : 0;
      }
      return this.selection.length;
    },
    // 是否禁用提示 true 禁用 false 不禁用
    disabledTip() {
      if (this.isNextStep) return true;
      if (this.isSelectedAllPages) {
        return false;
      }
      return new Set(this.selectionRow.map(item => item.os_type)).size <= 1;
    },

    // 操作系统是否筛选过一种 或者 仅存在一种, 那么跨页全选也是可批量操作的
    isSingleSystem() {
      return this.osTypeList.length === 1 || this.search.osType;
    },
    // 是否显示下一步 true显示 false 禁用
    isNextStep() {
      if (this.isSingleSystem) {
        return this.selectionCount;
      }
      return this.selectionRow.length > 0 && new Set(this.selectionRow.map(item => item.os_type)).size === 1;
    },
    currentOsType() {
      if (this.isNextStep) {
        if (this.isSelectedAllPages) {
          return this.search.osType;
        }
        const item = [...new Set(this.selectionRow.map(item => item.os_type))];
        return item[0];
      }
      return '';
    },
    checkAllPermission() {
      return this.table.data.length
        ? this.table.data.some(item => item.operate_permission)
        : true;
    },
    operateBizPermission() {
      if (this.permissionSwitch && !this.operateBiz.length) {
        return 'plugin_operate';
      }
      return '';
    },
  },
  watch: {
    searchSelectValue: {
      handler() {
        this.table.pagination.current = 1;
        this.initAgentListDebounce();
      },
      deep: true,
    },
  },
  created() {
    this.search.biz = this.selectedBiz;
    this.handleInit();
    this.getPluginFilter(); // 筛选条件接口拆分成为两个
  },
  mounted() {
    this.listenResize = debounce(300, v => this.handleResize(v));
    this.initAgentListDebounce = debounce(300, this.initAgentList);
    addListener(this.$el, this.listenResize);
  },
  beforeDestroy() {
    removeListener(this.$el, this.listenResize);
  },
  methods: {
    async handleInit() {
      this.loading = true;
      await PluginOldStore.getFilterCondition('plugin_host').then((data) => {
        const sysIndex = data.findIndex(item => item.id === 'os_type');
        try {
          if (sysIndex > -1) {
            const [sys] = data.splice(sysIndex, 1);
            const sysList = sys.children || [];
            if (sysList.length) {
              this.search.osType = sysList.find(item => item.id === 'LINUX') ? 'LINUX' : sysList[0].id;
            }
            this.osTypeList = sysList;
          }
        } catch (_) {}
        data.forEach((item) => {
          if (item.id === 'version') {
            item.showSearch = true;
            item.showCheckAll = true;
          }
        });
        this.filterData.unshift(...data);
        this.initRouteQuery();
      });
      this.initAgentList();
      // 拉取agent操作权限
      if (this.permissionSwitch) {
        this.getBizOperaPermission();
      }
    },
    async getPluginFilter() {
      await PluginOldStore.getFilterCondition('plugin_version').then((data) => {
        this.filterData.splice(this.filterData.length, 0, ...data);
      });
    },
    toggleExpansion(row) {
      this.$refs.hostTable.toggleRowExpansion(row);
    },
    getRowStyle({ row }) {
      return row.status === 'running' ? {} : { color: '#C3CDD7' };
    },
    stepHandle() {
      const params = {
        conditions: [],
        isAllChecked: this.isSelectedAllPages,
      };
      // 业务ID
      if (this.search.biz.length && this.search.biz.length !== this.bkBizList.length) {
        params.bk_biz_id = this.search.biz;
      }
      // 区分是否为跨页全选
      if (this.isSelectedAllPages) {
        params.exclude_hosts = this.markDeleteArr.map(item => item.bk_host_id) || [];
        // 如果未带有agent状态正常的筛选条件，需要补上
        const normalStatus = this.searchSelectValue.find(item => item.id === 'status');
        if (!normalStatus) {
          params.conditions.push({
            key: 'status',
            value: ['RUNNING'],
          });
        }
      } else {
        params.bk_host_id = this.selectionRow.map(item => item.bk_host_id) || [];
      }
      // 其他搜索条件
      this.searchSelectValue.forEach((item) => {
        if (Array.isArray(item.values)) {
          const valuesArr = item.values.map(v => v.id);
          params.conditions.push({
            key: item.id,
            value: valuesArr,
          });
        } else {
          params.conditions.push({
            key: 'query',
            value: item.name,
          });
        }
      });
      if (this.currentOsType) {
        params.os_type = this.currentOsType;
        params.conditions.push({
          key: 'os_type',
          value: [this.currentOsType],
        });
      }
      this.$emit('paramsChange', params);
      this.$emit('stepChange', 2);
    },
    /**
     * 初始化host列表
     * @param {Boolean} isKeepSearch 是否保留了搜索条件
     */
    async initAgentList(isKeepSearch = false) {
      this.loading = true;

      this.runingQueue.splice(0, this.runingQueue.length);
      clearTimeout(this.timer);
      this.timer = null;

      // const extraData = ['job_result', 'identity_info']
      // if (this.filter.topology.mockChecked) {
      //     extraData.push('topology')
      // }
      const params = this.getSearchCondition();
      const data = await PluginOldStore.getHostList(params);
      // 清除操作放后边，解决全选checkbox展示异常的问题
      if (!isKeepSearch) {
        this.isSelectedAllPages = false;
        this.markDeleteArr.splice(0, this.markDeleteArr.length);
        this.selectionRow.splice(0, this.selectionRow.length);
        this.handleClearSelection(); // 防止二次勾选时还是处于跨页全选状态
      }
      const selectLen = this.selectionRow.length;
      this.table.data = data.list.map((item) => {
        // 跨页勾选
        if (item.status === 'running') {
          if (this.isSelectedAllPages) {
            item.selection = !this.markDeleteArr.find(v => v.bk_host_id === item.bk_host_id);
          } else {
            item.selection = selectLen ? !!this.selectionRow.find(v => v.bk_host_id === item.bk_host_id) : false;
          }
        } else {
          item.selection = false;
        }
        // 常用的可筛选的官方插件放进表格初始化
        this.handleCommonPlugins(item, item.plugin_status || []);
        // 轮询任务队列{
        this.runingQueue.push(item.bk_host_id);
        return item;
      });
      this.table.pagination.count = data.total;
      this.loading = false;
      this.$nextTick(this.listenResize);
    },
    /**
     * 运行轮询任务
     */
    async handlePollData() {
      const data = await PluginOldStore.getHostList({
        page: 1,
        pagesize: this.runingQueue.length,
        bk_host_id: this.runingQueue,
        // extra_data: ['job_result', 'identity_info']
      });
      this.handleChangeStatus(data);
    },
    /**
     * 变更轮询回来的数据状态
     * @param {Object} data
     */
    handleChangeStatus(data) {
      data.list.forEach((item) => {
        const row = this.table.data.find(row => row.bk_host_id === item.bk_host_id);
        if (row) {
          row.status = item.status;
          row.status_display = item.status_display;
          row.version = item.version;
          this.handleCommonPlugins(row, item.plugin_status || []);
        }
      });
    },
    /**
     * 处理 plugin_status 带回来的四种常用官方插件信息
     */
    handleCommonPlugins(row, pluginStatus = []) {
      if (Array.isArray(pluginStatus)) {
        this.pluginList.forEach((key) => {
          const plugin = pluginStatus.find(item => key === item.name);
          // eslint-disable-next-line @typescript-eslint/prefer-optional-chain
          row[`${key}Status`] = plugin && plugin.status ? plugin.status.toLowerCase() : 'unknow';
          // eslint-disable-next-line @typescript-eslint/prefer-optional-chain
          row[`${key}Version`] = plugin && plugin.version ? plugin.version : '--';
        });
        row.plugin_status.splice(0, row.plugin_status.length, ...pluginStatus);
      }
    },
    getCommonCondition() {
      const params = {
        conditions: [],
      };
      // 业务ID
      if (this.search.biz.length && this.search.biz.length !== this.bkBizList.length) {
        params.bk_biz_id = this.search.biz;
      }
      // 其他搜索条件
      this.searchSelectValue.forEach((item) => {
        if (Array.isArray(item.values)) {
          params.conditions.push({
            key: item.id,
            value: item.values.map(value => value.id),
          });
        } else {
          params.conditions.push({
            key: 'query',
            value: item.name,
          });
        }
      });
      if (this.search.osType) {
        params.conditions.push({ key: 'os_type', value: [this.search.osType] });
      }
      return params;
    },
    /**
     * 获取主机列表当前所有查询条件
     */
    getSearchCondition(isSelectedAll = false) {
      const params = {
        pagesize: -1,
      };
      if (!isSelectedAll) {
        params.page = this.table.pagination.current;
        params.pagesize = this.table.pagination.limit;
      }

      return Object.assign(params, this.getCommonCondition());
    },
    /**
     * 标记删除法查询参数
     */
    getExcludeHostCondition(extraData = []) {
      const params = {
        pagesize: -1,
        exclude_hosts: this.markDeleteArr.map(item => item.bk_host_id),
        extra_data: extraData,
      };

      return Object.assign(params, this.getCommonCondition());
    },
    /**
     * 获取所有勾选IP信息查询条件
     */
    getCheckedIpCondition() {
      const params = {
        pagesize: -1,
        only_ip: true,
      };
      // 跨页全选
      if (this.isSelectedAllPages) {
        params.exclude_hosts = this.markDeleteArr.map(item => item.bk_host_id);
      }

      return Object.assign(params, this.getCommonCondition());
    },
    /**
     * 获取所有IP信息的查询条件
     */
    getAllIpCondition() {
      const params = {
        pagesize: -1,
        only_ip: true,
      };

      return Object.assign(params, this.getCommonCondition());
    },
    /**
     * 业务变更
     */
    handleBizChange() {
      this.table.pagination.current = 1;
      this.initAgentListDebounce();
    },
    handlePageChange(page) {
      this.table.pagination.current = page || 1;
      this.initAgentList(true);
    },
    handlePageLimitChange(limit) {
      this.table.pagination.limit = limit;
      this.handlePageChange();
    },
    /**
     * row勾选事件
     */
    handleRowCheck(arg, row) {
      // 跨页全选采用标记删除法
      if (this.isSelectedAllPages) {
        if (!arg[0]) {
          this.markDeleteArr.push(row);
        } else {
          const index = this.markDeleteArr.findIndex(item => item.bk_host_id === row.bk_host_id);
          if (index > -1) {
            this.markDeleteArr.splice(index, 1);
          }
        }
      } else {
        this.setSelectionRow(arg[0], [row]);
      }
      this.$set(row, 'selection', arg[0]);
    },
    stopBubble() {
      return false;
    },
    /**
     * 自定义selection表头
     */
    renderSelectionHeader(h) {
      return h(ColumnCheck, {
        ref: 'customSelectionHeader',
        props: {
          indeterminate: this.indeterminate,
          isAllChecked: this.isAllChecked,
          loading: this.checkLoading,
          disabled: this.disabledCheckBox,
          disabledCheckAll: this.disabledAllChecked,
          action: this.operateBizPermission,
          checkAllPermission: this.checkAllPermission,
        },
        on: {
          change: (value, type) => this.handleCheckAll(value, type),
        },
      });
    },
    /**
     * 表头勾选事件
     * @param {Boolean} value 全选 or 取消全选
     * @param {String} type 当前页全选 or 跨页全选
     */
    async handleCheckAll(value, type) {
      if (type === 'current' && this.disabledCheckBox) return;
      if (type === 'all') {
        this.checkLoading = true;
        // 防止轮询导致的请求取消
        const runingQueue = this.runingQueue.splice(0, this.runingQueue.length);
        clearTimeout(this.timer);
        await this.getCheckedCount();
        this.checkLoading = false;
        this.runingQueue = [...runingQueue];
      }
      this.isSelectedAllPages = value && type === 'all';
      this.markDeleteArr.splice(0, this.markDeleteArr.length);
      this.table.data.forEach((item) => {
        if (item.status === 'running' && (this.permissionSwitch ? item.operate_permission : true)) {
          this.$set(item, 'selection', value);
        }
      });
      this.setSelectionRow(value, type === 'all' ? {} : this.table.data.filter(row => row.status === 'running'), type);
    },
    /**
     * 非跨页全选时存储选中主机
     */
    setSelectionRow(value, rowArr, type = 'single') {
      if (type === 'all') {
        this.selectionRow.splice(0, this.selectionRow.length);
      } else {
        if (value) {
          rowArr.forEach((row) => {
            this.selectionRow.push(row);
          });
        } else {
          rowArr.forEach((row) => {
            const index = this.selectionRow.findIndex(item => item.bk_host_id === row.bk_host_id);
            if (index > -1) {
              this.selectionRow.splice(index, 1);
            }
          });
        }
      }
    },
    handleClearSelection() {
      bus.$emit('unchecked-all-agent');
    },
    /**
     * search select复制逻辑
     */
    handlePaste(e) {
      const [data] = e.clipboardData.items;
      data.getAsString((value) => {
        const { searchSelect } = this.$refs;
        let isIpType = false; // 是否为IP类型
        // 已选择特定类型的情况下 - 保持原有的粘贴行为（排除IP类型的粘贴）
        if (searchSelect.input && !isEmpty(searchSelect.input.value)) {
          const val = searchSelect.input.value;
          isIpType = /ip/i.test(searchSelect.input.value);
          Object.assign(e.target, { innerText: isIpType ? '' : val + value }); // 数据清空或合并
          this.$refs.searchSelect.handleInputChange(e); // 回填并响应数据
          this.$refs.searchSelect.handleInputFocus(e); // contenteditable类型 - 光标移动到最后
        } else {
          isIpType = true;
        }
        if (isIpType) {
          const str = value.replace(/;+|；+|_+|\\+|，+|,+|、+|\s+/g, ',').replace(/,+/g, ' ')
            .trim();
          const splitCode = ['，', ' ', '、', ',', '\n'].find(split => str.indexOf(split) > 0) || '\n';
          const tmpStr = str.trim().split(splitCode);
          const isIp = tmpStr.every(item => this.ipRegx.test(item));
          if (isIp) {
            this.handlePushValue('inner_ip', tmpStr.map(ip => ({
              id: ip,
              name: ip,
            })));
          } else {
            this.searchSelectValue.push({
              id: str.trim().replace('\n', ''),
              name: str.trim().replace('\n', ''),
            });
          }
        }
      });
    },
    /**
     * 单元格样式
     */
    handleCellClass({ column }) {
      if (column.property && column.property === 'topology') {
        return 'col-topology';
      }
    },
    /**
     * 当前操作项是否显示
     */
    getOperateShow(row, config) {
      if (config.id === 'log' && (!row.job_result || !row.job_result.job_id)) {
        return false;
      }
      return config.show;
    },
    handleResize() {
      this.isScroll = this.$el.scrollHeight + 60 > this.$root.$el.clientHeight - 52;
    },
    async getCheckedCount() {
      const params = this.getSearchCondition(true);
      const status = params.conditions.find(item => item.key === 'status');
      if (status) {
        if (!status.value.find(item => item === 'RUNNING')) {
          status.value.push('RUNNING');
        }
      } else {
        params.conditions.push({
          key: 'status',
          value: ['RUNNING'],
        });
      }
      const res = await PluginOldStore.getHostList(params);
      this.checkedCount = res.total;
      return res;
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
      if (column.property === this.pluginList[4]) {
        return [1, 2];
      } if (column.property === 'colspaSetting') {
        return [0, 0];
      }
    },
    /**
     * 拉取plugin操作权限的业务
     */
    async getBizOperaPermission() {
      const list = await MainStore.getBkBizPermission({ action: 'plugin_operate' });
      this.operateBiz = Array.isArray(list) ? list : [];
    },
    initRouteQuery() {
      const { cloud_id: cloudId, ip } = this.ipInfo;
      const values = [];
      if (!isEmpty(cloudId)) {
        const cloudClass = this.filterData.find(item => item.id === 'bk_cloud_id');
        const cloud = cloudClass ? (cloudClass.children || []).find(item => `${item.id}` === cloudId) : null;
        if (cloud) {
          values.push({
            name: '云区域',
            id: 'bk_cloud_id',
            values: [cloud],
          });
          this.handlePushValue('bk_cloud_id', [cloud], false);
        }
      }
      if (ip) {
        const host = { name: ip, id: ip };
        values.push({
          name: 'ip',
          id: 'inner_ip',
          values: [host],
        });
        this.handlePushValue('inner_ip', [host], false);
      }
      if (values.length) {
        this.handleSearchSelectChange(values);
      }
    },
  },
};
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";
  @import "@/css/transition.css";

  @define-mixin col-row-status $color {
    margin-right: 5px;
    margin-top: -1px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: $color;
  }

  .plugin-steps {
    padding: 20px 20px;
  }
  .tips-enter-active {
    transition: opacity .5s;
  }
  .tips-enter,
  .tips-leave-to {
    opacity: 0;
  }
  >>> .bk-icon.right-icon {
    margin-left: 6px;
  }
  >>> .bk-table-row .is-first .cell {
    text-align: left;
  }
  >>> .bk-dropdown-list {
    li {
      cursor: pointer;
    }
  }
  >>> .bk-table tr:hover {
    .col-num {
      background: #dcdee5;
    }
  }
  .agent {
    min-height: calc(100vh - 112px);
    padding-bottom: 82px;
    &-operate {
      @mixin layout-flex row, center, space-between;
      &-left {
        @mixin layout-flex row;
        .plugin-select {
          width: 160px;
        }
        .dropdown-btn {
          >>> .bk-button-loading {
            /* stylelint-disable-next-line declaration-no-important */
            background-color: unset !important;
            * {
              /* stylelint-disable-next-line declaration-no-important */
              background-color: #63656e !important;
            }
          }
        }
        .setup-btn {
          min-width: 130px;
        }
        .item-disabled {
          cursor: not-allowed;
          color: #c4c6cc;
          &:hover {
            background: transparent;
            color: #c4c6cc;
          }
        }
        .left-select {
          width: 160px;
          background: #fff;
        }
      }
      &-right {
        flex-basis: 400px;
        .right-select {
          background: #fff;
        }
      }
    }
    &-content {
      >>> .col-topology {
        .cell {
          padding-right: 0;
        }
      }
      .col-topo {
        cursor: default;
      }
      .col-num {
        background: #e6e8f0;
        border-radius: 8px;
        height: 14px;
        padding: 0 6px;
        margin-left: -15px;
      }
      .host-plugin {
        padding: 10px 20px 10px 85px;
        width: 100%;
        .host-plugin-item {
          float: left;
          width: 25%;
          line-height: 30px;
        }
      }
      .plugin-name {
        margin-right: 10px;
      }
      .plugin-version {
        color: #737987;
      }
      .inline-block {
        display: inline-block;
      }
      .col-operate {
        .reinstall {
          padding: 0;
          min-width: 24px;
        }
        .loading-icon {
          display: inline-block;
          animation: loading 1s linear infinite;
          font-size: 14px;
          min-width: 24px;
          text-align: center;
        }
        .loading-name {
          margin-left: 7px;
        }
        .link-icon {
          font-size: 14px;
        }
      }
      .selection-tips {
        height: 30px;
        background: #ebecf0;

        @mixin layout-flex row, center, center;
        .tips-num {
          font-weight: bold;
        }
        .tips-btn {
          font-size: 12px;
          margin-left: 5px;
        }
      }
      .pagination {
        margin-top: -1px;
        padding: 14px 16px;
        height: 60px;
        border: 1px solid #dcdee5;
        background: #fff;
        >>> .bk-page-total-count {
          color: #63656e;
        }
        >>> .bk-page-count {
          margin-top: -1px;
        }
      }
    }
  }
  .bk-plugin-button {
    position: absolute;
    width: 100%;
    bottom: 0;
    text-align: center;
    button {
      min-width: 100px;
    }
  }
  .agent-content {
    position: relative;
    padding-bottom: 48px;
  }
  .footer-fixed {
    .bk-plugin-button {
      position: fixed;
      right: 14px;
      padding: 10px 0;
      border-top: 1px solid #e2e2e2;
      background: #fff;
      z-index: 5;
    }
  }
</style>
