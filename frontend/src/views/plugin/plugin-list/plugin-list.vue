<template>
  <article class="plugin-node" v-bkloading="{ isLoading: loading }" v-test="'pluginList'">
    <PluginListOperate
      :search-select-data="filterData"
      :selections="selections"
      :exclude-data="excludeData"
      :check-type="checkType"
      :running-count="runningCount"
      :strategy-value="strategyValue"
      v-model="searchSelectValue"
      @filter-change="handleFilterChange"
      @plugin-operate="handlePluginOperate">
    </PluginListOperate>
    <PluginListTable
      v-bkloading="{ isLoading: tableLoading }"
      class="plugin-node-table"
      :table-list="tableList"
      :pagination="pagination"
      :search-select-data="filterData"
      :selection-loading="selectionLoading"
      :selections="selections"
      :exclude-data="excludeData"
      :head-select-disabled="selectedAllDisabled"
      :check-value="checkValue"
      :check-type="checkType"
      :running-count="runningCount"
      @selection-change="handleSelectionChange"
      @row-check="handleRowCheck"
      @filter-confirm="tableHeaderConfirm"
      @filter-reset="tableHeaderReset"
      @sort="handleTableSort"
      @pagination-change="handlePaginationChange">
    </PluginListTable>
    <bk-dialog
      :width="isZh ? 600 : 630"
      header-position="left"
      ext-cls="operate-dialog"
      :mask-close="false"
      :value="dialogInfo.show"
      :title="dialogInfo.title"
      @cancel="handleDialogCancel">
      <template #default>
        <bk-form v-test="'operateForm'" :label-width="isZh ? 90 : 128">
          <bk-form-item :label="$t('操作范围')">
            <i18n path="已选择插件">
              <b class="num">{{ operateNum }}</b>
            </i18n>
          </bk-form-item>
          <bk-form-item :label="$t('插件操作')" required>
            <div :class="['bk-button-group', { 'is-zh': isZh }]">
              <bk-button
                v-for="item in pluginOperateList"
                :key="item.id"
                v-test="item.id"
                ext-cls="btn-item"
                :class="dialogInfo.operate === item.id ? 'is-selected' : ''"
                v-bk-tooltips="{
                  content: item.tips,
                  disabled: !item.tips
                }"
                @click="dialogInfo.operate = item.id">
                {{ item.name }}
              </bk-button>
            </div>
          </bk-form-item>
          <bk-form-item :label="$t('选择插件')" required>
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
  </article>
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

  private loading = false;
  private tableLoading = false;
  private selectionLoading = false;
  private tableList: IPluginList[] = [];
  private pagination: IPagination = {
    current: 1,
    count: 0,
    limit: 20,
  };
  private selections: IPluginList[] = [];
  private excludeData: IPluginList[] = [];
  private allData: ITarget[] = []; // 跨页全选得到的数据
  private checkType: 'current' | 'all' = 'current';
  private runningCount = 0;
  private checkValue: CheckValueEnum = 0;
  private hasOldRouteParams = false;
  private osMap = {
    LINUX: 'Linux',
    WINDOWS: 'Windows',
    AIX: 'AIX',
  };
  private strategyValue: Array<number | string> = []; // 插件id number， 策略名称 string
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
  private pluginOperateList = [
    { id: 'MAIN_INSTALL_PLUGIN', name: window.i18n.t('安装或更新') },
    { id: 'MAIN_START_PLUGIN', name: window.i18n.t('启动') },
    { id: 'MAIN_STOP_PLUGIN', name: window.i18n.t('停止') },
    { id: 'MAIN_RESTART_PLUGIN', name: window.i18n.t('重启') },
    { id: 'MAIN_RELOAD_PLUGIN', name: window.i18n.t('重载') },
    {
      id: 'MAIN_DELEGATE_PLUGIN',
      name: window.i18n.t('托管'),
      tips: window.i18n.t('将插件注册到GSEAgent管理当插件异常退出时可尝试进行自动拉起'),
    },
    {
      id: 'MAIN_UNDELEGATE_PLUGIN',
      name: window.i18n.t('取消托管'),
      tips: window.i18n.t('取消插件的GSEAgent管理当插件异常退出时将不再被自动拉起'),
    },
  ];
  private mixisPluginName: string[] = []; // 插件的状态和版本筛选条件组合到了一起
  private pluginStatusMap: { [key: string]: string[] } = {}; // 插件的状态列表

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
    return MainStore.language === 'zh';
  }

  @Watch('searchSelectValue', { deep: true })
  public handleSearchValeuChange() {
    this.pagination.current = 1;
    const params = this.getCommonParams();
    this.handleSearch(params);
  }

  private created() {
    const { policyId = '', pluginName } = this.$route.params;
    const pluginNameStr = this.pluginName || pluginName;
    if (policyId) { // 部署策略跳转过来
      this.strategyValue.push(parseInt(policyId, 10));
    }
    // 适配旧的路由
    let params: Dictionary = {};
    if ([this.ip, this.cloudId, this.osType].some(item => !isEmpty(item))) {
      this.hasOldRouteParams = true;
      params = this.getInitFilterParams();
    }
    if (pluginNameStr) { // 插件包跳转过来
      this.searchSelectValue.push({
        id: 'plugin_name',
        multiable: true,
        name: window.i18n.t('插件名称'),
        values: [{ checked: true, id: pluginNameStr, name: pluginNameStr }],
      });
    }
    this.handleInitData(this.hasOldRouteParams ? params as ISearchParams : undefined);
  }

  public async handleInitData(data?: ISearchParams) {
    this.loading = true;
    const params = data || this.getCommonParams();
    const promiseList: Promise<any>[] = [
      this.getFilterData(),
      this.getHostList(params),
    ];
    this.getPluginFilter();
    await Promise.all(promiseList);
    this.loading = false;
  }

  // 拉取筛选条件 并 插入插件名称项
  public async getFilterData() {
    const [
      list,
      { list: data2 },
    ] = await Promise.all([PluginStore.getFilterList(), PluginStore.pluginPkgList({ simple_all: true })]);
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
        label: `${item.name}(${item.description})`,
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
  }
  public async getPluginFilter() {
    await PluginStore.getFilterList({ category: 'plugin_version' }).then((data) => {
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
      this.mixisPluginName = statusName;
      this.filterData.splice(this.filterData.length, 0, ...data.filter(item => !statusReg.test(item.id)));
    });
  }

  public async getHostList(params: ISearchParams) {
    const data: IHostData = await PluginStore.getHostList(params);
    const { list, total } = data;
    this.tableList = list;
    this.pagination.count = total;
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
            console.log(...getFilterChildBySelected(item.id, child.name, this.filterData));
            value.push(...getFilterChildBySelected(item.id, child.name, this.filterData).map(item => item.id));
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
    if (this.strategyValue.length) {
      conditions.push({ key: 'source_id', value: [...this.strategyValue] });
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

  private handleFilterChange({ type, value }: { type: 'biz'|'strategy'|'search', value: any }) {
    if (type === 'search') {
      this.searchSelectValue = value;
      this.handleSearchSelectChange(value);
      this.handleResetCheck();
    } else {
      if (type === 'strategy') {
        this.strategyValue = value;
      } else if (type === 'biz') {
        this.strategyValue = [];
      }
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

  private async handlePluginOperate() {
    this.dialogInfo.show = true;
    this.dialogInfo.operate = 'MAIN_INSTALL_PLUGIN';
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
}

</script>
<style lang="postcss" scoped>
  .plugin-node .plugin-node-table {
    margin-top: 14px;
  }
  .operate-dialog {
    .num {
      color: #3a84ff;
    }
    .bk-button-group {
      margin-bottom: 10px;
      .btn-item {
        width: 114px;
        margin-bottom: 10px;
        span {
          display: inline-block;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
        }
      }
      &.is-zh .btn-item {
        width: 93px;
      }
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
