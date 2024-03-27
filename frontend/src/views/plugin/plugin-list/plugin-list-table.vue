<template>
  <section>
    <bk-table
      ref="nodeListTable"
      v-test="'listTable'"
      :max-height="tableMaxHeight"
      :class="`head-customize-table ${ fontSize }`"
      :data="tableList"
      :pagination="pagination"
      @page-change="paginationChange(arguments, 'page')"
      @page-limit-change="paginationChange(arguments, 'pageSize')"
      @sort-change="handleSort">
      <template #prepend>
        <SelectionTips
          select-all-text
          v-show="!selectionLoading && checkValue === 2"
          :selection-count="selectionCount"
          :total="pagination.count"
          :select-all-data="checkType === 'all'"
          @select-all="handleSelectAll"
          @clear="handleClearSelections">
        </SelectionTips>
      </template>
      <bk-table-column
        width="60"
        align="left"
        class-name="checkbox-row"
        :resizable="false"
        :render-header="renderSelectionHeader"
        fixed>
        <template #default="{ row }">
          <div class="checkbox-row-item">
            <bk-popover placement="right" :disabled="row.status === 'RUNNING'">
              <bk-checkbox
                v-test="'rowSelect'"
                :value="getRowCheckStatus(row)"
                :disabled="row.status !== 'RUNNING'"
                @change="handleRowSelect($event, row)"
                @click.native.stop>
              </bk-checkbox>
              <template slot="content">
                {{ $t('Agent无法选择', [row.status === 'NOT_INSTALLED' ? $t('未安装lower') : $t('状态异常')]) }}
              </template>
            </bk-popover>
            <div class="col-status ">
              <span :class="`status-mark status-${row.status.toLowerCase()}`"></span>
            </div>
          </div>
        </template>
      </bk-table-column>
      <NmColumn
        min-width="130"
        prop="inner_ip"
        class-name="ip-row"
        sortable
        :label="$t('内网IPv4')"
        fixed>
        <template #default="{ row }">
          <a class="nm-link" v-if="row.inner_ip" v-test="'showDetail'" text @click="handleRowClick(row)">
            {{ row.inner_ip }}
          </a>
          <span v-else>{{ row.inner_ip | filterEmpty }}</span>
        </template>
      </NmColumn>
      <NmColumn
        v-if="filterField['inner_ipv6'] && filterField['inner_ipv6'].mockChecked"
        :width="innerIPv6Width"
        prop="inner_ipv6"
        class-name="ip-row"
        :label="$t('内网IPv6')"
        fixed>
        <template #default="{ row }">
          <a class="nm-link" v-if="row.inner_ipv6" v-test="'showDetail'" text @click="handleRowClick(row)">
            {{ row.inner_ipv6 }}
          </a>
          <span v-else>{{ row.inner_ipv6 | filterEmpty }}</span>
        </template>
      </NmColumn>
      <NmColumn
        v-if="filterField['bk_host_name'].mockChecked"
        min-width="140"
        prop="bk_host_name"
        sortable
        :label="$t('主机名')"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          {{ row.bk_host_name | filterEmpty }}
        </template>
      </NmColumn>
      <NmColumn
        key="bk_agent_id"
        label="Agent ID"
        prop="bk_agent_id"
        width="260"
        v-if="filterField['bk_agent_id'].mockChecked">
        <template #default="{ row }">
          {{ row.bk_agent_id | filterEmpty }}
        </template>
      </NmColumn>
      <NmColumn
        key="bk_host_id"
        label="Host ID"
        prop="bk_host_id"
        width="80"
        v-if="filterField['bk_host_id'].mockChecked" />
      <NmColumn
        v-if="filterField['node_type'].mockChecked"
        min-width="120"
        prop="node_type"
        sortable
        :label="$t('节点类型')"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          {{ row.node_type | filterEmpty }}
        </template>
      </NmColumn>
      <NmColumn
        min-width="130"
        prop="bk_cloud_id"
        sortable
        :label="$t('管控区域')"
        v-if="filterField['bk_cloud_id'].mockChecked"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          <span>{{ row.bk_cloud_name | filterEmpty }}</span>
        </template>
      </NmColumn>
      <NmColumn
        min-width="155"
        prop="bk_biz_name"
        :label="$t('归属业务')"
        sortable
        v-if="filterField['bk_biz_name'].mockChecked">
      </NmColumn>
      <NmColumn
        v-if="filterField['os_type'].mockChecked"
        min-width="145"
        prop="os_type"
        :label="$t('操作系统')"
        sortable
        :resizable="false"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          {{ osMap[row.os_type] | filterEmpty }}
        </template>
      </NmColumn>
      <NmColumn
        v-if="filterField['bk_addressing'] && filterField['bk_addressing'].mockChecked"
        min-width="130"
        prop="bk_addressing"
        :label="$t('寻址方式')">
        <template #default="{ row }">
          {{ `${row.bk_addressing}` === 'dynamic' ? $t('动态') : $t('静态') }}
        </template>
      </NmColumn>
      <template v-for="(plugin, index) in pluginNames">
        <NmColumn
          :min-width="columnMinWidth[plugin]"
          :key="index"
          :label="plugin"
          :prop="plugin"
          :render-header="renderFilterHeader"
          :show-overflow-tooltip="false"
          v-if="filterField[plugin] && filterField[plugin].mockChecked">
          <template #default="{ row }">
            <div class="col-status">
              <span :class="`status-mark status-${getRowPluginInfo(plugin, row)}`"></span>
              <span class="text-ellipsis" v-bk-overflow-tips>{{ getRowPluginInfo(plugin, row, 'version') }}</span>
            </div>
          </template>
        </NmColumn>
      </template>
      <!--自定义字段显示列-->
      <NmColumn
        key="setting"
        prop="colspaSetting"
        :render-header="renderSettingHeader"
        width="42"
        fixed="right"
        :resizable="false">
      </NmColumn>
      <NmException
        slot="empty"
        :delay="tableLoading"
        :type="tableEmptyType"
        @empty-clear="emptySearchClear"
        @empty-refresh="emptyRefresh" />
    </bk-table>
    <node-detail-slider
      :loading="loading"
      :bk-host-id="currentHostId"
      :ip="currentIp"
      :detail-data="detailData"
      :status="currentHostStatus"
      v-model="showSlider">
    </node-detail-slider>
  </section>
</template>
<script lang="ts">
import { Mixins, Component, Prop, Watch, Emit, Ref } from 'vue-property-decorator';
import { MainStore, PluginStore as PluginState } from '@/store';
import { IPluginList, IPluginStatus } from '@/types/plugin/plugin-type';
import { IPagination, CheckValueEnum, ISearchItem, ITabelFliter } from '@/types';
import HeaderRenderMixin from '@/components/common/header-render-mixins';
import ColumnSetting from '@/components/common/column-setting.vue';
import ColumnCheck from '@/components/common/column-check.vue';
import NodeDetailSlider from './node-detail-slider.vue';
import SelectionTips from '@/components/common/selection-tips.vue';
import PluginStatusBox from './plugin-status-box.vue';
import { CreateElement } from 'vue';
import { DHCP_FILTER_KEYS } from '@/config/config';

@Component({
  name: 'plugin-list-table',
  components: {
    NodeDetailSlider,
    SelectionTips,
    PluginStatusBox,
  },
})
export default class PluginRuleTable extends Mixins(HeaderRenderMixin) {
  @Prop({ default: () => ({
    limit: 50,
    current: 1,
    count: 0,
    limitList: [50, 100, 200],
  }), type: Object,
  }) private readonly pagination!: IPagination;
  @Prop({ default: () => ([]), type: Array }) private readonly tableList!: IPluginList[];
  @Prop({ default: () => ([]), type: Array }) private readonly searchSelectData!: ISearchItem[];
  @Prop({ default: false, type: Boolean }) private readonly tableLoading!: boolean;
  @Prop({ default: () => ([]), type: Array }) private readonly searchSelectValue!: ISearchItem[];
  @Prop({ default: false, type: Boolean }) private readonly selectionLoading!: boolean;
  // 0 未选 1 半选 2 全选
  @Prop({ default: 0, type: Number }) private readonly checkValue!: CheckValueEnum;
  @Prop({ default: false, type: Boolean }) private readonly headSelectDisabled!: boolean;
  @Prop({ default: 'current', type: String }) private readonly checkType!: 'current' | 'all';
  @Prop({ default: 0, type: Number }) private readonly runningCount!: number;
  @Prop({ default: () => [], type: Array }) private readonly selections!: IPluginList[];
  @Prop({ default: () => [], type: Array }) private readonly excludeData!: IPluginList[];
  @Prop({ default: () => [], type: Array }) private readonly pluginNames!: string[];

  @Ref('nodeListTable') private readonly nodeListTable!: any;

  private get fontSize() {
    return MainStore.fontSize;
  }

  private get tableMaxHeight() {
    return MainStore.windowHeight - 180 - (MainStore.noticeShow ? 40 : 0);
  }

  @Watch('searchSelectData', { deep: true, immediate: true })
  private handleSearchSelectDataChange(data: ISearchItem[]) {
    this.filterData = JSON.parse(JSON.stringify(data));
  }
  @Watch('selectionCount')
  private handleSelectionkChange() {
    this.$nextTick(() => {
      this.nodeListTable.doLayout();
    });
  }

  private currentIp = '';
  private currentHostId = -1;
  private currentHostStatus = '';
  private showSlider = false;
  // 本地存储Key
  private localMark = 'plugin_list_table';
  private filterField: { [key: string]: ITabelFliter } = {
    inner_ip: {
      checked: true,
      disabled: true,
      name: window.i18n.t('内网IPv4'),
      id: 'inner_ip',
      mockChecked: true,
    },
    inner_ipv6: {
      checked: this.$DHCP,
      disabled: this.$DHCP,
      name: window.i18n.t('内网IPv6'),
      id: 'inner_ipv6',
      mockChecked: this.$DHCP,
    },
    bk_host_name: {
      checked: true,
      disabled: false,
      name: window.i18n.t('主机名'),
      id: 'bk_host_name',
      mockChecked: true,
    },
    bk_agent_id: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: 'Agent ID',
      id: 'bk_agent_id',
    },
    bk_host_id: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: 'Host ID',
      id: 'bk_host_id',
    },
    node_type: {
      checked: true,
      disabled: false,
      name: window.i18n.t('节点类型'),
      id: 'node_type',
      mockChecked: true,
    },
    bk_cloud_id: {
      checked: true,
      disabled: false,
      name: window.i18n.t('管控区域'),
      id: 'bk_cloud_id',
      mockChecked: true,
    },
    bk_biz_name: {
      checked: true,
      disabled: false,
      name: window.i18n.t('归属业务'),
      id: 'bk_biz_name',
      mockChecked: true,
    },
    os_type: {
      checked: true,
      disabled: false,
      name: window.i18n.t('操作系统'),
      id: 'os_type',
      mockChecked: true,
    },
    bk_addressing: {
      checked: false,
      disabled: false,
      name: window.i18n.t('寻址方式'),
      id: 'bk_addressing',
      mockChecked: false,
    },
    // {
    //   checked: true,
    //   disabled: false,
    //   name: window.i18n.t('Agent状态'),
    //   id: 'agent_status'
    // },
  };
  private popoverIns: any = null;
  private loading = false;
  private detailData: IPluginStatus[] = [];
  private statusMap: Dictionary = {
    pending: this.$t('队列中'), // 队列中
    running: this.$t('部署中'), // 部署中
    success: this.$t('正常'), // 成功
    failed: this.$t('异常'),   // 失败
  };

  private get osMap() {
    return MainStore.osMap;
  }
  private get selectionCount() {
    if (this.checkType === 'current') {
      return this.selections.length;
    }
    return this.runningCount - this.excludeData.length;
  }
  private get innerIPv6Width() {
    const ipv6SortRows: number[] = this.tableList
      .filter(row => !!row.inner_ipv6)
      .map(row => row.inner_ipv6.length)
      .sort((a, b) => b - a);
    return ipv6SortRows.length ? Math.ceil(ipv6SortRows[0] * 6.9) : 80;
  }
  private get columnMinWidth(): Dictionary {
    return this.pluginNames.reduce((obj, plugin) => {
      Object.assign(obj, { [plugin]: this.$textTool.getHeadWidth(plugin, { filter: true, extra: 2 }) });
      return obj;
    }, {});
  }
  private get tableEmptyType() {
    return this.searchSelectValue.length ? 'search-empty' : 'empty';
  }

  private created() {
    this.filterData.splice(0, this.filterData.length, ...JSON.parse(JSON.stringify(this.searchSelectData)));
    this.pluginNames.forEach((name) => {
      this.$set(this.filterField, name, { name, id: name, checked: true, disabled: false, mockChecked: true });
    });
  }

  private renderSelectionHeader(h: CreateElement) {
    return h(ColumnCheck, {
      props: {
        value: this.checkValue,
        loading: this.selectionLoading,
        defaultCheckType: this.checkType,
        disabled: this.headSelectDisabled || this.tableList.length === 0,
      },
      on: {
        change: this.handleSelectionChange,
      },
      ref: 'columnCheck',
    });
  }
  private renderSettingHeader(h: CreateElement) {
    return h(ColumnSetting, {
      props: {
        localMark: this.localMark,
        value: this.filterField,
        filterHead: true,
      },
      on: {
        update: this.handleFieldCheckChange,
      },
    });
  }
  private handleFieldCheckChange(filter: { [key: string]: ITabelFliter }) {
    const localFilter = JSON.parse(JSON.stringify(filter));
    if (!this.$DHCP) {
      const columnsFilter: Dictionary = {};
      Object.keys(localFilter).forEach((key) => {
        if (!DHCP_FILTER_KEYS.includes(key)) {
          columnsFilter[key] = localFilter[key];
        }
      });
      this.$set(this, 'filterField', columnsFilter);
    } else {
      this.$set(this, 'filterField', localFilter);
    }
    this.$forceUpdate();
  }
  private handleClearSelections() {
    this.handleSelectionChange({ value: CheckValueEnum.uncheck, type: 'current' });
  }
  private handleSelectAll() {
    this.handleSelectionChange({ value: CheckValueEnum.checked, type: 'all' });
  }
  @Emit('selection-change')
  private handleSelectionChange({ value, type }: { value: CheckValueEnum, type: 'current' | 'all' }) {
    this.$nextTick(() => {
      this.nodeListTable.doLayout();
    });
    return {
      value,
      type,
    };
  }
  @Emit('row-check')
  private handleRowSelect(value: boolean, row: IPluginList) {
    return {
      value,
      row,
    };
  }
  @Emit('pagination-change')
  private handlePaginationChange(value: number, type: 'page' | 'pageSize') {
    return { value, type };
  }
  @Emit('sort')
  private handleSort({ prop, order }: { prop: string, order: string }) {
    return {
      prop,
      order: order === 'ascending' ? 'ASC' : 'DEC',
    };
  }

  // 查看主机任务
  public handleRowClick(row: IPluginList) {
    this.currentIp = row.inner_ip || row.inner_ipv6;
    this.currentHostId = row.bk_host_id;
    this.currentHostStatus = row.status;
    this.handleLoadDetaitl();
    this.showSlider = true;
  }
  public async handleLoadDetaitl() {
    this.loading = true;
    const list = await PluginState.getHostPolicy({
      bk_host_id: this.currentHostId,
    });
    this.detailData = list;
    this.loading = false;
  }
  public getRowPluginInfo(plugin: string, row: IPluginList, type = 'status') {
    const data = row.plugin_status.find(item => item.name === plugin);
    if (!data) {
      return type === 'status' ? 'unknown' : '--';
    }
    return type === 'status' ? data.status.toLowerCase() || 'unknown' : data.version || '--';
  }
  public getRowCheckStatus(row: IPluginList) {
    if (row.status !== 'RUNNING') return false;

    if (this.checkType === 'current') {
      return this.selections.some(item => item.bk_host_id === row.bk_host_id);
    }
    return this.excludeData.every(item => item.bk_host_id !== row.bk_host_id);
  }
  public paginationChange(value: number[], type: 'page' | 'pageSize') {
    this.handlePaginationChange(value[0], type);
  }
}
</script>

<style lang="postcss" scoped>
  >>> .checkbox-row .cell {
    padding-right: 8px;
  }
  >>> .ip-row {
    .cell {
      padding-left: 0;
    }
  }
  .checkbox-row-item {
    display: flex;
    .col-status {
      position: relative;
      left: 10px;
    }
  }
  .badge-strategy-group {
    display: inline-flex;
    .badge-item {
      padding: 0 5px;
      height: 16px;
      line-height: 16px;
      border-radius: 2px;
      font-size: 12px;
      font-weight: 600;
      background: #ccc;
      &.success {
        color: #3fc06d;
        background: #e5f6ea;
      }
      &.failed {
        color: #ea3636;
        background: #ffe6e6;
      }
      &.running {
        color: #3a84ff;
        background: #e1ecff;
      }
    }
    .badge-item + .badge-item {
      margin-left: 4px;
    }
  }
</style>
