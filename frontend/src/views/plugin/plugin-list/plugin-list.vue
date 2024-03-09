<template>
  <section class="plugin-node" v-bkloading="{ isLoading: loading }" v-test="'pluginList'">
    <PluginListOperate
      :search-select-data="filterData"
      :selections="selections"
      :exclude-data="excludeData"
      :check-type="checkType"
      :running-count="runningCount"
      :operate-more="pluginOperateMore"
      :total="pagination.count"
      v-model="searchSelectValue"
      @filter-change="handleFilterChange"
      @plugin-operate="handlePluginOperate">
    </PluginListOperate>
    <PluginListTable
      v-if="!loading"
      v-bkloading="{ isLoading: tableLoading }"
      class="plugin-node-table"
      :table-list="tableList"
      :pagination="pagination"
      :table-loading="tableLoading"
      :search-select-data="filterData"
      :search-select-value="searchSelectValue"
      :selection-loading="selectionLoading"
      :selections="selections"
      :exclude-data="excludeData"
      :head-select-disabled="selectedAllDisabled"
      :check-value="checkValue"
      :check-type="checkType"
      :running-count="runningCount"
      :plugin-names="mixisPluginName"
      @selection-change="handleSelectionChange"
      @row-check="handleRowCheck"
      @filter-confirm="tableHeaderConfirm"
      @filter-reset="tableHeaderReset"
      @sort="handleTableSort"
      @pagination-change="handlePaginationChange"
      @empty-clear="searchClear"
      @empty-refresh="getHostList">
    </PluginListTable>
    <bk-dialog
      :width="isZh ? 620 : 728"
      header-position="left"
      ext-cls="operate-dialog"
      :mask-close="false"
      :value="dialogInfo.show"
      :title="dialogInfo.title"
      @cancel="handleDialogCancel">
      <template #default>
        <bk-form form-type="vertical" v-test="'operateForm'">
          <div class="bk-form-item" style="display: flex;">
            <label class="bk-label">
              <span class="bk-label-text">{{ $t('操作范围') }}</span>
            </label>
            <div class="bk-form-content">
              <i18n path="已选择插件">
                <b class="num">{{ operateNum }}</b>
              </i18n>
            </div>
          </div>
          <bk-form-item :label="$t('选择插件')" required style="z-index: 0;">
            <bk-select
              v-test="'pluginName'"
              ext-cls="plugin-select"
              searchable
              :popover-options="{ 'boundary': 'HTMLElement' }"
              v-model="dialogInfo.plugin">
              <bk-option
                v-for="option in pluginList"
                :key="option.id"
                :id="option.name"
                :name="option.label">
              </bk-option>
            </bk-select>
          </bk-form-item>
        </bk-form>
      </template>
      <template #footer>
        <div class="footer">
          <bk-button
            v-test.common="'formCommit'"
            theme="primary"
            :disabled="!dialogInfo.plugin"
            @click="handleDialogConfirm">
            {{ $t('下一步') }}
          </bk-button>
          <bk-button class="ml10" @click="handleDialogCancel">{{ $t('取消') }}</bk-button>
        </div>
      </template>
    </bk-dialog>
  </section>
</template>
<script lang="ts">
import { Component, Watch, Mixins, Prop } from 'vue-property-decorator';
import { PluginStore, MainStore } from '@/store';
import PluginListOperate from './plugin-list-operate.vue';
import PluginListTable from './plugin-list-table.vue';
import { IPluginList, ISearchParams, ICondition, IHostData, IPluginRow, ITarget } from '@/types/plugin/plugin-type';
import { debounceDecorate, getFilterChildBySelected, isEmpty } from '@/common/util';
import HeaderFilterMixins from '@/components/common/header-filter-mixins';
import { IPagination, CheckValueEnum, ISortData, ISearchChild, ISearchItem } from '@/types';

interface IPluginMap {
  name: string
  checkedAll: boolean
  children: number[]
}

@Component({
  name: 'plugin-list',
  components: {
    PluginListOperate,
    PluginListTable,
  },
})
export default class PluginList extends Mixins(HeaderFilterMixins) {
  @Prop({ type: String, default: '' }) private readonly  ip!: string;
  @Prop({ type: String, default: '' }) private readonly  cloudId!: string;
  @Prop({ type: String, default: '' }) private readonly  osType!: string;
  @Prop({ type: String, default: '' }) private readonly  pluginName!: string;

  private loading = true;
  private tableLoading = false;
  private selectionLoading = false;
  private tableList: IPluginList[] = [];
  private pagination: IPagination = {
    current: 1,
    count: 0,
    limit: 50,
    limitList: [50, 100, 200],
  };
  private selections: IPluginList[] = [];
  private excludeData: IPluginList[] = [];
  private allData: ITarget[] = []; // 跨页全选得到的数据
  private checkType: 'current' | 'all' = 'current';
  private runningCount = 0;
  private checkValue: CheckValueEnum = 0;
  private hasOldRouteParams = false;
  private sortData: ISortData = {
    head: '',
    sort_type: '',
  };
  private pluginList: IPluginRow[] = [];
  private dialogInfo = {
    show: false,
    title: window.i18n.t('批量插件操作'),
    operate: '',
    plugin: '',
  };
  private pluginOperateMore = [
    { id: 'MAIN_START_PLUGIN', name: window.i18n.t('启动') },
    { id: 'MAIN_STOP_PLUGIN', name: window.i18n.t('停止') },
    { id: 'MAIN_RESTART_PLUGIN', name: window.i18n.t('重启') },
    { id: 'MAIN_RELOAD_PLUGIN', name: window.i18n.t('重载') },
    {
      id: 'MAIN_DELEGATE_PLUGIN',
      name: window.i18n.t('托管'),
      tips: window.i18n.t('托管插件Tips'),
    },
    {
      id: 'MAIN_UNDELEGATE_PLUGIN',
      name: window.i18n.t('取消托管'),
      tips: window.i18n.t('停用托管插件Tips'),
    },
  ];
  private mixisPluginName: string[] = []; // 插件的状态和版本筛选条件组合到了一起
  private pluginStatusMap: { [key: string]: string[] } = {}; // 插件的状态列表
  private showMore = false;

  private get selectedAllDisabled() {
    const statusCondition = this.searchSelectValue.find(item => item.id === 'status');
    return statusCondition ? !(statusCondition.values as ISearchChild[]).find(item => item.id === 'RUNNING') : false;
  }
  private get operateNum() {
    return this.checkType === 'all' ? this.runningCount - this.excludeData.length : this.selections.length;
  }
  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  private get isZh() {
    return MainStore.language === 'zh-cn';
  }
  private get isMoreSelected() {
    return this.pluginOperateMore.find(item => item.id === this.dialogInfo.operate);
  }

  @Watch('searchSelectValue', { deep: true })
  public handleSearchValeuChange() {
    this.pagination.current = 1;
    const params = this.getCommonParams();
    this.handleSearch(params);
  }
  @Watch('selectedBiz')
  public handleBizSelect() {
    this.getStrategyTopo();
    this.pagination.current = 1;
    const params = this.getCommonParams();
    this.handleSearch(params);
  }

  private async created() {
    this.loading = true;
    const { policyId = '', policyName, pluginName } = this.$route.params;
    const pluginNameStr = this.pluginName || pluginName;
    const initValue = [];
    if (policyId) { // 部署策略跳转过来
      initValue.push({
        id: 'source_id',
        name: window.i18n.t('部署策略'),
        multiable: true,
        values: [{ checked: true, id: policyId, name: policyName }],
      });
    }
    // 适配旧的路由
    let initParams: Dictionary = {};
    if ([this.ip, this.cloudId, this.osType].some(item => !isEmpty(item))) {
      this.hasOldRouteParams = true;
      initParams = this.getInitFilterParams();
    }
    if (pluginNameStr) { // 插件包跳转过来
      initValue.push({
        id: 'plugin_name',
        multiable: true,
        name: window.i18n.t('插件名称'),
        values: [{ checked: true, id: pluginNameStr, name: pluginNameStr }],
      });
    }
    if (initValue.length) {
      this.searchSelectValue.push(...initValue);
    }
    Promise.all([this.getPluginFilter(), this.getStrategyTopo()]).then(([len, children]) => {
      this.filterData.splice(len, 0, {
        id: 'source_id',
        name: window.i18n.t('部署策略'),
        multiable: true,
        children,
      });
    });
    const params = this.hasOldRouteParams ? initParams as ISearchParams : this.getCommonParams();
    if (this.$route.params.policyId) {
      // 修正部署策略接口未加载完毕的错误筛选条件
      const sourceConditions = params.conditions.find(item => item.key === 'source_id');
      if (sourceConditions) {
        sourceConditions.value = [this.$route.params.policyId];
      }
    }
    this.getFilterData();// 修复filter condition接口慢阻塞UI问题
    await this.getHostList(params);
    this.loading = false;
  }

  // 拉取筛选条件 并 插入插件名称项
  public async getFilterData() {
    const [
      data,
      { list: data2 },
    ] = await Promise.all([PluginStore.getFilterList(), PluginStore.pluginPkgList({ simple_all: true })]);
    this.mixisPluginName = data.filter(item => item.children && !item.children.length).map(item => item.id);
    const list = data.filter(item => !item.children || item.children.length);
    if (data2.length) {
      const pluginName = this.pluginName || this.$route.params.pluginName;
      const pluginItem = {
        id: 'plugin_name',
        name: window.i18n.t('插件名称'),
        multiable: true,
        children: data2.map(item => ({
          checked: item.name === pluginName,
          id: item.name,
          name: item.name,
        })),
      };
      list.push(pluginItem);

      this.pluginList = data2.filter(item => item.is_ready).map(item => ({
        label: item.description ? `${item.name}(${item.description})` : item.name,
        ...item,
      }));
    }
    if (this.hasOldRouteParams) {
      const inputValues = [];
      if (!isEmpty(this.cloudId)) {
        const filterItem = this.setFilterChildChecked(list, 'bk_cloud_id', parseInt(this.cloudId, 10));
        if (filterItem) {
          inputValues.push(filterItem);
        }
      }
      if (!isEmpty(this.osType)) {
        const filterItem = this.setFilterChildChecked(list, 'os_type', this.osType.toUpperCase());
        if (filterItem) {
          inputValues.push(filterItem);
        }
      }
      if (this.ip) {
        const ips = this.ip.replace(/\s/g, '').split(',');
        inputValues.push({
          id: 'inner_ip',
          name: 'IP',
          values: ips.map(ip => ({ checked: false, id: ip, name: ip })),
        });
      }
      if (inputValues.length) {
        this.searchSelectValue.splice(this.searchSelectValue.length, 0, ...inputValues);
      }
    }
    this.filterData.splice(0, 0, ...list);
    return Promise.resolve(true);
  }
  public async getPluginFilter() {
    const data = await PluginStore.getFilterList({ category: 'plugin_version' });
    const statusName: string[] = [];
    const statusReg = /_status/;
    data.forEach((item) => {
      if (!statusReg.test(item.id)) {
        const statusItem = data.find(child => child.id === `${item.id}_status`);
        this.pluginStatusMap[item.id] = statusItem?.children?.map(item => item.id) || [];
        if (statusItem) {
          item.name = item.id;
          item.children?.splice(0, 0, ...(statusItem.children || []));
          statusName.push(item.id);
        }
      }
    });
    const filters = data.filter(item => !statusReg.test(item.id));
    this.filterData.splice(this.filterData.length, 0, ...filters);
    return filters.length;
  }

  public async getHostList(params: ISearchParams) {
    const data: IHostData = await PluginStore.getHostList(params);
    const { list, total } = data;
    this.tableList = list;
    this.pagination.count = total;
    return Promise.resolve(true);
  }
  private async getStrategyTopo() {
    const params: Dictionary = {};
    if (this.selectedBiz.length) {
      params.bk_biz_ids = this.selectedBiz;
    }
    const res = await PluginStore.fetchPolicyTopo(params);
    const children = res.reduce((list: any[], item) => {
      const arr = (item.children || []).map(child => ({ id: child.id, name: `${child.name}-${item.name}`, checked: false }));
      if (arr.length) {
        list.push(...arr);
      }
      return list;
    }, []);
    const index = this.filterData.findIndex(item => item.id === 'source_id');
    if (index > -1) {
      this.filterData.splice(index, 1, {
        id: 'source_id',
        name: window.i18n.t('部署策略'),
        multiable: true,
        children,
      });
    }
    return children;
  }

  // 获取请求参数
  public getCommonParams() {
    const params: ISearchParams = {
      page: this.pagination.current,
      pagesize: this.pagination.limit,
      conditions: this.getConditions(),
    };
    if (this.selectedBiz && this.selectedBiz.length) {
      params.bk_biz_id = this.selectedBiz;
    }
    if (this.sortData.head && this.sortData.sort_type) {
      params.sort = Object.assign({}, this.sortData);
    }
    return params;
  }

  public getConditions(type: 'load' | 'operate' = 'load') {
    const conditions: ICondition[] = [];
    this.searchSelectValue.forEach((item) => {
      // 从插件里区分状态和版本
      if (this.mixisPluginName.includes(item.id)) {
        const values = item.values || [];
        const status = values.filter(child => this.pluginStatusMap[item.id].includes(child.id));
        const version = values.filter(child => !this.pluginStatusMap[item.id].includes(child.id));
        if (status.length) {
          conditions.push({
            key: `${item.id}_status`,
            value: status.map(value => value.id),
          });
        }
        if (version.length) {
          conditions.push({
            key: item.id,
            value: version.map(value => value.id),
          });
        }
      } else {
        if (Array.isArray(item.values)) {
          const value: string[] = [];
          item.values.forEach((child) => {
            value.push(...getFilterChildBySelected(item.id, child.id, this.filterData).map(item => item.id));
          });
          conditions.push({ key: item.id, value });
        } else {
          conditions.push({ key: 'query', value: item.name });
        }
      }
    });
    if (type === 'operate') { // 跨页全选和操作
      const statusIndex = conditions.findIndex(item => item.key === 'status');
      const runCondition = { key: 'status', value: ['RUNNING'] };
      if (statusIndex > -1) {
        conditions.splice(statusIndex, 1, runCondition);
      } else {
        conditions.push(runCondition);
      }
    }
    return conditions;
  }

  @debounceDecorate(300)
  private async handleSearch(params: ISearchParams) {
    this.tableLoading = true;
    await this.getHostList(params);
    this.tableLoading = false;
  }

  // 获取运行中的主机数量，用于统计跨页全选总数
  private async getRunningHosts() {
    this.selectionLoading = true;
    const params: ISearchParams = {
      pagesize: -1,
      simple: true,
      conditions: this.getConditions('operate'),
    };
    if (this.selectedBiz && this.selectedBiz.length) {
      params.bk_biz_id = this.selectedBiz;
    }
    const index = params.conditions.findIndex(item => item.key === 'status');
    if (index > -1) {
      params.conditions.splice(index, 1);
    }
    params.conditions.push({
      key: 'status',
      value: ['RUNNING'],
    });
    const { total, list }: IHostData = await PluginStore.getHostList(params);
    this.runningCount = total;
    this.allData = list;
    this.selectionLoading = false;
  }

  private async handleSelectionChange({ value, type }: { value: CheckValueEnum, type: 'current' | 'all' }) {
    this.checkValue = value;
    if (type === 'all' && value === CheckValueEnum.checked) {
      await this.getRunningHosts();
    }
    this.checkType = type;
    this.excludeData = [];
    this.selections = type === 'current' && value === CheckValueEnum.checked
      ? [...this.tableList.filter((row: IPluginList) => row.status === 'RUNNING')] : [];
  }

  private handleRowCheck({ value, row }: { value: boolean, row: IPluginList }) {
    if (this.checkType === 'current') {
      if (value) {
        this.selections.push(row);
      } else {
        const index = this.selections.findIndex(item => item.bk_host_id === row.bk_host_id);
        index > -1 && this.selections.splice(index, 1);
      }
      // 重新计算当前页未被check的数据
      this.excludeData = this.tableList.reduce<IPluginList[]>((pre, next) => {
        if (this.selections.indexOf(next) === -1) {
          pre.push(next);
        }
        return pre;
      }, []);
    } else {
      if (value) {
        const index = this.excludeData.findIndex(item => item.bk_host_id === row.bk_host_id);
        index > -1 && this.excludeData.splice(index, 1);
      } else {
        this.excludeData.push(row);
      }
    }
    this.updateCheckStatus();
  }

  private updateCheckStatus() {
    // 设置当前check状态
    if (!this.tableList.length) {
      this.checkValue = 0;
    } else if (this.excludeData.length === 0) {
      // 未选
      this.checkValue = 2;
    } else if ([this.pagination.count, this.tableList.length].includes(this.excludeData.length)) {
      // 取消全选
      this.checkValue = 0;
      this.checkType = 'current';
      this.selections = [];
    } else {
      // 半选
      this.checkValue = 1;
    }
  }

  private handleFilterChange({ type, value }: { type: 'biz'|'search', value: any }) {
    if (type === 'search') {
      this.searchSelectValue = value;
      this.handleSearchSelectChange(value);
      this.handleResetCheck();
    } else {
      this.pagination.current = 1;
      const params = this.getCommonParams();
      this.handleSearch(params);
    }
  }

  private handleResetCheck() {
    this.selections = [];
    this.excludeData = [];
    this.checkType = 'current';
    this.checkValue = 0;
  }

  private async handlePluginOperate(operate: string) {
    this.dialogInfo.show = true;
    this.dialogInfo.operate = operate;
  }

  // 安装/更新 走手动流程
  private async handleDialogConfirm() {
    const { operate, plugin } = this.dialogInfo;
    const { id, name } = this.pluginList.find(item => item.name === plugin) as IPluginRow;
    // 参数格式同策略, 安装 / 更新 需要传steps, 其他操作不需要
    const strategyData: Dictionary = {
      job_type: operate,
      plugin_name: plugin,
      plugin_info: { id, name  },
      configs: [],
      params: [],
      steps: [{ id: plugin, type: 'PLUGIN', configs: [], params: [] }],
      scope: {
        object_type: 'HOST',
        node_type: 'INSTANCE',
        nodes: this.checkType === 'current'
          ? this.selections.map(item => ({ bk_biz_id: item.bk_biz_id, bk_host_id: item.bk_host_id }))
          : this.allData.filter(item => !this.excludeData.some(exclude => exclude.bk_host_id === item.bk_host_id)),
      },
    };
    this.$router.push({
      name: 'pluginOperation',
      params: { type: operate, pluginId: id, pluginName: name, strategyData },
    });
  }

  private handleDialogCancel() {
    this.dialogInfo.show = false;
    this.dialogInfo.operate = '';
    this.dialogInfo.plugin = '';
  }

  private async handlePaginationChange(pagination: { value: number, type: 'page' | 'pageSize' }) {
    if (pagination.type === 'pageSize') {
      this.pagination.limit = pagination.value;
      this.pagination.current = 1;
    } else {
      this.pagination.current = pagination.value;
    }
    this.checkType === 'current' && this.handleResetCheck();
    this.tableLoading = true;
    const params = this.getCommonParams();
    await this.getHostList(params);
    this.tableLoading = false;
  }

  private handleTableSort({ prop, order }: { prop: string, order: string }) {
    Object.assign(this.sortData, { head: prop, sort_type: order });
    this.handlePaginationChange({ type: 'page', value: 1 });
  }
  // 拿到初始化时表格请求的参数
  private getInitFilterParams() {
    const params = this.getCommonParams();
    if (this.osType) {
      params.conditions.push({ key: 'os_type', value: [this.osType.toUpperCase()] });
    }
    if (this.cloudId) {
      params.conditions.push({ key: 'bk_cloud_id', value: [parseInt(this.cloudId, 10)] });
    }
    if (this.ip) {
      const ips = this.ip.replace(/\s/g, '').split(',');
      params.conditions.push({ key: 'inner_ip', value: ips });
    }
    return params;
  }
  // 初始化时设置表头筛选以及获得输入框的填充
  private setFilterChildChecked(data: ISearchItem[], classId: string, childId: string | number) {
    const currentFilter = data.find(item => item.id === classId);
    if (currentFilter) {
      const child = currentFilter.children?.find(item => item.id === childId);
      if (child) {
        child.checked = true;
        return {
          id: currentFilter.id,
          name: currentFilter.name,
          multiable: true,
          values: [child],
        };
      }
    }
    return false;
  }
  public searchClear() {
    this.tableLoading = true;
    this.searchSelectValue = [];
    this.handleSearchSelectChange([]);
  }
}

</script>
<style lang="postcss" scoped>
  .flex-center {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .dropdown-icon-absolute {
    position: relative;
    font-size: 14px;
    .bk-icon {
      position: absolute;
      right: 0px;
      top: 7px;
    }
  }
  .plugin-node {
    flex: 1;
    .plugin-node-table {
      margin-top: 14px;
    }
  }
  .operate-dialog {
    .num {
      color: #3a84ff;
    }
    .bk-form-item:last-child {
      margin-top: 0;
    }
  }
  .plugin-select {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    background: #fff;
    z-index: 5;
  }
  .footer {
    font-size: 0;
    button {
      min-width: 76px;
    }
  }
</style>
