<template>
  <section>
    <bk-table
      ref="nodeListTable"
      v-test="'listTable'"
      :max-height="windowHeight - 180"
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
      <bk-table-column
        min-width="130"
        prop="inner_ip"
        class-name="ip-row"
        sortable
        :label="$t('内网IP')"
        fixed>
        <template #default="{ row }">
          <bk-button v-test="'showDetail'" text @click="handleRowClick(row)">{{ row.inner_ip }}</bk-button>
        </template>
      </bk-table-column>
      <bk-table-column
        v-if="getColumnShowStatus('node_type')"
        min-width="120"
        prop="node_type"
        sortable
        :label="$t('节点类型')"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          {{ row.node_type | filterEmpty }}
        </template>
      </bk-table-column>
      <bk-table-column
        min-width="120"
        prop="bk_cloud_id"
        sortable
        :label="$t('云区域')"
        v-if="getColumnShowStatus('bk_cloud_id')"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          <span>{{ row.bk_cloud_name | filterEmpty }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        min-width="120"
        prop="bk_biz_name"
        :label="$t('归属业务')"
        sortable
        v-if="getColumnShowStatus('bk_biz_name')">
      </bk-table-column>
      <bk-table-column
        v-if="getColumnShowStatus('os_type')"
        min-width="115"
        prop="os_type"
        :label="$t('操作系统')"
        sortable
        :resizable="false"
        :render-header="renderFilterHeader">
        <template #default="{ row }">
          {{ osMap[row.os_type] | filterEmpty }}
        </template>
      </bk-table-column>
      <template v-for="(plugin, index) in officialPlugin">
        <bk-table-column
          min-width="108"
          :key="index"
          :label="plugin"
          :prop="plugin"
          :render-header="renderFilterHeader"
          v-if="getColumnShowStatus(plugin)">
          <template #default="{ row }">
            <div class="col-status">
              <span :class="`status-mark status-${getRowPluginInfo(plugin, row)}`"></span>
              <span>{{ getRowPluginInfo(plugin, row, 'version') }}</span>
            </div>
          </template>
        </bk-table-column>
      </template>
      <!--自定义字段显示列-->
      <bk-table-column
        key="setting"
        prop="colspaSetting"
        :render-header="renderSettingHeader"
        width="42"
        :resizable="false">
      </bk-table-column>
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
import FormLabelMixin from '@/common/form-label-mixin';
import SelectionTips from '@/components/common/selection-tips.vue';
import PluginStatusBox from './plugin-status-box.vue';
import { CreateElement } from 'vue';

@Component({
  name: 'plugin-list-table',
  components: {
    NodeDetailSlider,
    SelectionTips,
    PluginStatusBox,
  },
})
export default class PluginRuleTable extends Mixins(FormLabelMixin, HeaderRenderMixin) {
  @Prop({ default: () => ({
    limit: 50,
    current: 1,
    count: 0,
    limitList: [50, 100, 200],
  }), type: Object,
  }) private readonly pagination!: IPagination;
  @Prop({ default: () => ([]), type: Array }) private readonly tableList!: IPluginList[];
  @Prop({ default: () => ([]), type: Array }) private readonly searchSelectData!: ISearchItem[];
  @Prop({ default: false, type: Boolean }) private readonly selectionLoading!: boolean;
  // 0 未选 1 半选 2 全选
  @Prop({ default: 0, type: Number }) private readonly checkValue!: CheckValueEnum;
  @Prop({ default: false, type: Boolean }) private readonly headSelectDisabled!: boolean;
  @Prop({ default: 'current', type: String }) private readonly checkType!: 'current' | 'all';
  @Prop({ default: 0, type: Number }) private readonly runningCount!: number;
  @Prop({ default: () => [], type: Array }) private readonly selections!: IPluginList[];
  @Prop({ default: () => [], type: Array }) private readonly excludeData!: IPluginList[];

  @Ref('nodeListTable') private readonly nodeListTable!: any;

  private get fontSize() {
    return MainStore.fontSize;
  }

  private get windowHeight() {
    return MainStore.windowHeight;
  }

  @Watch('searchSelectData', { deep: true })
  private handleSearchSelectDataChange(data: ISearchItem[]) {
    this.filterData = JSON.parse(JSON.stringify(data));
  }
  @Watch('selectionCount')
  private handleSelectionkChange() {
    this.$nextTick(() => {
      this.nodeListTable.doLayout();
    });
  }

  private officialPlugin: string[] = ['basereport', 'processbeat', 'exceptionbeat', 'bkunifylogbeat', 'bkmonitorbeat'];
  private currentIp = '';
  private currentHostId = -1;
  private currentHostStatus = '';
  private showSlider = false;
  private osMap = {
    LINUX: 'Linux',
    WINDOWS: 'Windows',
    AIX: 'AIX',
  };
  // 本地存储Key
  private localMark = 'plugin_list_table';
  private filterField: ITabelFliter[] = [];
  private popoverIns: any = null;
  private loading = false;
  private detailData: IPluginStatus[] = [];
  private statusMap: Dictionary = {
    pending: this.$t('队列中'), // 队列中
    running: this.$t('部署中'), // 部署中
    success: this.$t('正常'), // 成功
    failed: this.$t('异常'),   // 失败
  };

  private get selectionCount() {
    if (this.checkType === 'current') {
      return this.selections.length;
    }
    return this.runningCount - this.excludeData.length;
  }

  private created() {
    const plugin = this.officialPlugin.map(name => ({
      name,
      id: name,
      checked: true,
      disabled: false,
    }));
    this.filterField = [
      {
        checked: true,
        disabled: true,
        name: 'IP',
        id: 'inner_ip',
      },
      {
        checked: true,
        disabled: false,
        name: this.$t('节点类型'),
        id: 'node_type',
      },
      {
        checked: true,
        disabled: false,
        name: window.i18n.t('云区域'),
        id: 'bk_cloud_id',
      },
      {
        checked: true,
        disabled: false,
        name: window.i18n.t('归属业务'),
        id: 'bk_biz_name',
      },
      {
        checked: true,
        disabled: false,
        name: window.i18n.t('操作系统'),
        id: 'os_type',
      },
      // {
      //   checked: true,
      //   disabled: false,
      //   name: window.i18n.t('Agent状态'),
      //   id: 'agent_status'
      // },
      ...plugin,
    ];
  }

  private getColumnShowStatus(id: string) {
    const item = this.filterField.find(item => item.id === id);
    return !!item?.checked;
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
  private handleFieldCheckChange(filter: ITabelFliter[]) {
    this.filterField = JSON.parse(JSON.stringify(filter));
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
    this.currentIp = row.inner_ip;
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
  >>> .bk-table-fixed {
    /* stylelint-disable-next-line declaration-no-important */
    bottom: 0 !important;
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
