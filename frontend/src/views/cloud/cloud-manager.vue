<template>
  <article class="cloud-manager" v-test="'cloudManager'">
    <!--提示-->
    <section class="cloud-tips mb20">
      <tips :list="tipsList"></tips>
    </section>
    <!--内容区域-->
    <section class="cloud-content">
      <div class="content-header mb15">
        <div class="h32">
          <!--创建管控区域-->
          <auth-component
            tag="div"
            :authorized="authority.create_action"
            :apply-info="[{ action: 'cloud_create' }]">
            <template slot-scope="{ disabled }">
              <bk-button
                v-test="'addCloud'"
                theme="primary"
                :disabled="disabled"
                ext-cls="header-btn"
                @click="handleAddCloud">
                {{ $t("新建") }}
              </bk-button>
            </template>
          </auth-component>
          <CopyDropdown
            class="ml10"
            :list="copyMenu"
            :disabled="!checkableRowsAll"
            :get-ips="handleCopyIp" />
        </div>
        <!--搜索管控区域-->
        <bk-input
          v-test="'searchCloud'"
          :placeholder="$t('搜索名称')"
          right-icon="bk-icon icon-search"
          ext-cls="header-input"
          v-model.trim="searchValue"
          @change="handleValueChange">
        </bk-input>
      </div>

      <!--管控区域列表-->
      <div class="content-table" v-bkloading="{ isLoading: loading }">
        <bk-table
          v-test="'cloudTable'"
          :class="`head-customize-table ${ fontSize }`"
          :max-height="tableMaxHeight"
          :pagination="pagination"
          :span-method="colspanHandle"
          :data="tableData"
          :row-class-name="rowClassName"
          @page-change="handlePageChange"
          @page-limit-change="handlePageLimitChange"
          @row-click="handleExpandChange"
          @sort-change="handleSortChange">
          <bk-table-column
            key="selection"
            width="70"
            :render-header="renderSelectionHeader">
            <template #default="{ row }">
              <div @click.stop>
                <bk-checkbox
                  v-if="!row.isChannel"
                  :value="row.selected"
                  :disabled="!row.proxyCount"
                  @change="handleRowCheck(arguments, row)">
                </bk-checkbox>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column class-name="fs10 col-pad-none" width="25" prop="expand" :resizable="false">
            <template #default="{ row }">
              <div
                v-if="!row.isChannel"
                :class="['bk-table-expand-icon', { 'bk-table-expand-icon-expanded': row.expand }]">
                <i class="bk-icon icon-play-shape"></i>
              </div>
            </template>
          </bk-table-column>
          <NmColumn
            class-name="col-pl-none"
            sortable="custom"
            :label="$t('管控区域名称')"
            prop="cloudNameCopy"
          >
            <template #default="{ row }">
              <div v-if="row.isChannel" class="channel-name">
                <i class="nodeman-icon nc-parenet-node-line channel-icon"></i>
                <span>{{ row.name }}</span>
              </div>
              <auth-component
                v-else
                v-test="'viewDetail'"
                :class="{ 'nm-link text-btn': permissionSwitch ? row.view : true }"
                :authorized="row.view"
                :apply-info="[{
                  action: 'cloud_view',
                  instance_id: row.bkCloudId,
                  instance_name: row.bkCloudName
                }]"
                @click="handleGotoDetail(row)">
                {{ row.bkCloudName }}
              </auth-component>
            </template>
          </NmColumn>
          <NmColumn :label="$t('管控区域ID')" prop="bkCloudId" width="110" />
          <NmColumn align="right" width="55" :resizable="false">
            <template #default="{ row }">
              <img :src="`data:image/svg+xml;base64,${row.ispIcon}`" class="col-svg" v-if="row.ispIcon">
            </template>
          </NmColumn>
          <NmColumn :label="$t('云服务商')" prop="ispName" sortable="custom">
            <template #default="{ row }">
              <span v-if="!row.isChannel">{{ row.ispName | filterEmpty }}</span>
            </template>
          </NmColumn>
          <NmColumn
            :label="$t('可用Proxy数量')"
            width="140"
            prop="aliveProxyCount"
            align="right"
            :resizable="false"
            :show-overflow-tooltip="false"
            sortable="custom">
            <template #default="{ row }">
              <section v-if="!row.isChannel">
                <auth-component
                  v-if="row.proxyCount"
                  class="auth-inline pr20"
                  tag="div"
                  :authorized="row.view"
                  :apply-info="[{
                    action: 'cloud_view',
                    instance_id: row.bkCloudId,
                    instance_name: row.bkCloudName
                  }]">
                  <template slot-scope="{ disabled }">
                    <bk-popover width="240" placement="top" :disabled="row.aliveProxyCount > 1">
                      <bk-button
                        ext-cls="col-btn"
                        theme="primary"
                        text
                        :disabled="disabled"
                        v-test="'viewDetail'"
                        @click="handleGotoDetail(row)">
                        {{ row.aliveProxyCount }}
                        <span
                          v-if="row.aliveProxyCount < 2"
                          :class="`count-icon ${row.aliveProxyCount === 1 ? 'warning' : 'danger'}`">!</span>
                      </bk-button>
                      <div slot="content">
                        {{ !row.aliveProxyCount ? $t('proxy数量提示0') : $t('proxy数量提示') }}
                      </div>
                    </bk-popover>
                  </template>
                </auth-component>
                <auth-component
                  v-else
                  class="auth-inline pr20"
                  :authorized="!!proxyOperateList.length"
                  :apply-info="[{ action: 'proxy_operate' }]">
                  <template slot-scope="{ disabled }">
                    <span class="install-proxy" :disabled="disabled" v-bk-tooltips="$t('点击前往安装')">
                      <span v-test="'instalProxy'" @click="handleInstallProxy(row)">{{ $t('未安装') }}</span>
                      <span class="count-error-text">!</span>
                    </span>
                  </template>
                </auth-component>
              </section>
            </template>
          </NmColumn>
          <NmColumn :label="$t('Agent数量')" prop="nodeCount" align="right" :resizable="false" sortable="custom">
            <template #default="{ row }">
              <div class="pr20">
                <span v-if="row.nodeCount" class="text-btn" v-test="'filterAgent'" @click.stop="handleGotoAgent(row)">
                  {{ row.nodeCount }}
                </span>
                <span v-else>0</span>
              </div>
            </template>
          </NmColumn>
          <NmColumn align="right" width="40" />
          <NmColumn :label="$t('接入点')" prop="apName" />
          <NmColumn
            prop="colspaOpera"
            :label="$t('操作')"
            :width="fontSize === 'large' ? 175 : 155"
            :resizable="false">
            <template #default="{ row }">
              <div v-if="!row.isChannel">
                <auth-component
                  tag="div"
                  :authorized="row.view && !!proxyOperateList.length"
                  :apply-info="row.view ? [{ action: 'proxy_operate' }] : [
                    {
                      action: 'proxy_operate'
                    },
                    {
                      action: 'cloud_view',
                      instance_id: row.bkCloudId,
                      instance_name: row.bkCloudName
                    }
                  ]">
                  <template slot-scope="{ disabled }">
                    <bk-button
                      text
                      v-test="'instalProxy'"
                      ext-cls="col-btn"
                      theme="primary"
                      :disabled="disabled"
                      @click="handleInstallProxy(row)">
                      {{ $t("Proxy安装") }}
                    </bk-button>
                  </template>
                </auth-component>
                <auth-component
                  class="auth-inline"
                  tag="div"
                  :authorized="row.edit"
                  :apply-info="[{
                    action: 'cloud_edit',
                    instance_id: row.bkCloudId,
                    instance_name: row.bkCloudName
                  }]">
                  <template slot-scope="{ disabled }">
                    <bk-button
                      v-test="'editCloud'"
                      ext-cls="col-btn ml10"
                      theme="primary" text
                      :disabled="disabled"
                      @click="handleEdit(row)">
                      {{ $t("编辑") }}
                    </bk-button>
                  </template>
                </auth-component>
                <auth-component
                  class="auth-inline"
                  tag="div"
                  :authorized="row.delete"
                  :apply-info="[{
                    action: 'cloud_delete',
                    instance_id: row.bkCloudId,
                    instance_name: row.bkCloudName
                  }]">
                  <template slot="default" slot-scope="{ disabled }">
                    <bk-popover :content="deleteTips" :disabled="!(row.proxyCount || row.nodeCount)" class="ml10">
                      <bk-button
                        v-test="'deleteCloud'"
                        ext-cls="col-btn"
                        :disabled="disabled || !!(row.proxyCount || row.nodeCount)"
                        theme="primary"
                        text
                        @click="handleDelete(row)">
                        {{ $t("删除") }}
                      </bk-button>
                    </bk-popover>
                  </template>
                </auth-component>
              </div>
            </template>
          </NmColumn>
          <!--自定义字段显示列-->
          <NmColumn
            key="setting"
            prop="colspaSetting"
            :render-header="renderHeader"
            width="42"
            :resizable="false">
          </NmColumn>

          <NmException
            slot="empty"
            :delay="loading"
            :type="tableEmptyType"
            @empty-clear="searchClear"
            @empty-refresh="handleValueChange" />
        </bk-table>
      </div>
    </section>
  </article>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { MainStore, CloudStore } from '@/store/index';
import { IBkColumn } from '@/types';
import { ICloud } from '@/types/cloud/cloud';
import Tips from '@/components/common/tips.vue';
import ColumnSetting from '@/components/common/column-setting.vue';
import ColumnCheck from '@/views/agent/components/column-check.vue';
import { debounce, sort } from '@/common/util';
import { cloudSort } from './config/cloud-common';
import { CreateElement } from 'vue';
import CopyDropdown, { allChildList, checkedChildList } from '@/components/common/copy-dropdown.vue';

interface ICloudRow extends ICloud {
  expand?: boolean
  isChannel?: boolean
  selected: boolean
  cloudNameCopy?: string
  children: ICloudRow[]
}
type ISortProp = null | 'cloudNameCopy' | 'ispName' | 'proxyCount' | 'nodeCount';
type ISortOrder = null | 'ascending' | 'descending';

@Component({
  name: 'cloud-manager',
  components: {
    Tips,
    CopyDropdown,
  },
})

export default class CloudManager extends Vue {
  @Prop({ type: Number, default: 0 }) private readonly id!: number; // 编辑ID

  // 提示信息
  private tipsList = [
    this.$t('管控区域管理提示一'),
  ];
  // 表格属性
  private table: {
    list: any[]
    data: ICloudRow[]
  } = {
    list: [],
    data: [],
  };
  private tableData: ICloudRow[] = [];
  private pagination = {
    current: 1,
    limit: 20,
    count: 0,
  };
  // 搜索值
  private searchValue = '';
  // 支持搜索的字段
  private searchParams = [
    'bkCloudName',
    'bkCloudId',
    'ispName',
    'apName',
  ];
  // 搜索防抖
  private handleValueChange() {}
  private sortProp: ISortProp = null;
  private sortOrder: ISortOrder = null;
  // 表格加载
  private loading = false;
  // 删除操作禁用提示
  private deleteTips = this.$t('删除禁用提示');
  private isSelectAllPages = false;
  private excludedRows: ICloudRow[] = [];

  private get fontSize() {
    return MainStore.fontSize;
  }
  private get permissionSwitch() {
    return MainStore.permissionSwitch;
  }
  private get authority() {
    return CloudStore.authority;
  }
  private get proxyOperateList() {
    return this.authority.proxy_operate || [];
  }
  private get tableMaxHeight() {
    return MainStore.windowHeight - 240 - (MainStore.noticeShow ? 40 : 0);
  }
  // 是否已选择
  private get hasSelectedRows() {
    return this.tableData.some(item => !!item.selected);
  }
  // 当前页可是否可全选
  private get checkableRows() {
    return this.tableData.some(item => !!item.proxyCount);
  }
  // 是否可跨页全选
  private get checkableRowsAll() {
    return this.table.data.some(item => !!item.proxyCount);
  }
  // 当前是否是半选状态
  private get indeterminate() {
    if (this.isSelectAllPages) {
      // 跨页全选半选状态
      return !this.isAllChecked && !!this.excludedRows.length;
    }
    return !this.isAllChecked && this.tableData.some(item => item.selected);
  }
  // 是当前否为全选
  private get isAllChecked() {
    if (this.isSelectAllPages) {
      // 标记删除的数组为空
      return !this.excludedRows.length;
    }
    return this.tableData.every(item => item.selected || !item.proxyCount)
      && !this.tableData.every(item => !item.proxyCount);
  }
  protected get copyMenu() {
    return [
      {
        name: this.$t('勾选管控区域的ProxyIP'),
        id: 'selected',
        disabled: !this.hasSelectedRows,
        child: this.$DHCP ? checkedChildList : [],
      },
      {
        name: this.$t('所有管控区域的ProxyIP'),
        id: 'all',
        child: this.$DHCP ? allChildList : [],
      },
    ];
  }
  private get tableEmptyType() {
    return this.searchValue.length ? 'search-empty' : 'empty';
  }

  private created() {
    this.handleInit();
  }
  private mounted() {
    this.handleValueChange = debounce(300, () => this.handleSearch());
  }

  /**
   * 初始化
   */
  public async handleInit() {
    this.loading = true;
    const promiseAll = [CloudStore.getCloudList(), CloudStore.getChannelList()];
    const res = await Promise.all(promiseAll);
    const data = res[0] as ICloud[];
    const channelList = res[1];
    const sortData = cloudSort(data, this.permissionSwitch); // 管控区域排序
    CloudStore.SET_CLOUD_LIST([...sortData]);

    // 留下一份基础排序的数据, 后续优化均从此数据上二次排序
    this.table.list = sortData.map((item: ICloud) => {
      const children: Dictionary[] = [
        { id: 'default', name: this.$t('默认通道'), nodeCount: 0, isChannel: true, bk_cloud_id: item.bkCloudId },
      ];
      const filterChannels = channelList.filter((channel: Dictionary) => channel.bk_cloud_id === item.bkCloudId)
        .map((channel: Dictionary) => ({ ...channel, isChannel: true }));
      children.push(...filterChannels);

      return {
        ...item,
        expand: false,
        selected: false,
        cloudNameCopy: item.bkCloudName.toLocaleLowerCase(),
        children,
      };
    });
    this.handleSearch();
  }
  /**
   * 前端搜索
   */
  public handleSearch(page = 1) {
    const { table, sortProp, sortOrder } = this;
    table.list.forEach(item => item.selected = false);
    let tableData = [...this.table.list];
    if (this.searchValue.length > 0) {
      const value = this.searchValue.toLocaleLowerCase();
      tableData = tableData.filter((item: any) => this.searchParams
        .some(param => item[param] && ~(item[param]).toString().toLocaleLowerCase()
          .indexOf(value)));
    }
    if (sortProp) {
      if (['cloudNameCopy', 'ispName'].includes(sortProp)) {
        sort(tableData, sortProp);
      } else {
        tableData.sort((prev, next) => prev[sortProp] - next[sortProp]);
      }
      if (sortOrder === 'descending') {
        tableData.reverse();
      }
    }
    this.table.data = tableData;
    this.pagination.count = tableData.length;
    this.handlePageChange(page);
    this.loading = false;
  }
  /**
   * 编辑
   * @param {Object} row
   */
  public handleEdit(row: ICloud) {
    this.$router.push({
      name: 'addCloudManager',
      params: {
        id: `${row.bkCloudId}`,
        type: 'edit',
      },
    });
  }
  /**
   * 删除
   * @param {Object} row
   */
  public handleDelete(row: ICloud) {
    const deleteCloud = async (id: number) => {
      this.loading = true;
      const result = await CloudStore.deleteCloud(id);
      if (result) {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.handleInit();
      } else {
        this.loading = false;
      }
    };
    this.$bkInfo({
      title: this.$t('确定删除该管控区域'),
      extCls: 'wrap-title',
      confirmFn: () => {
        deleteCloud(row.bkCloudId);
      },
    });
  }
  /**
   * 添加管控区域
   */
  public handleAddCloud() {
    this.$router.push({
      name: 'addCloudManager',
      params: {
        type: 'add',
      },
    });
  }
  /**
   * 跳转详情
   * @param {Object} row
   */
  public handleGotoDetail(row: ICloud) {
    this.$router.push({
      name: 'cloudManagerDetail',
      params: {
        id: `${row.bkCloudId}`,
        loaded: true,
      },
    });
  }
  /**
   * 新增Proxy
   */
  public handleInstallProxy(row: ICloud) {
    this.$router.push({
      name: 'setupCloudManager',
      params: {
        type: 'create',
        id: `${row.bkCloudId}`,
      },
    });
  }
  /**
   * 自定义字段显示列
   * @param {createElement 函数} h 渲染函数
   */
  public renderHeader(h: CreateElement) {
    return h(ColumnSetting);
  }
  /**
   * 合并最后两列
   */
  public colspanHandle({ column }: { column: IBkColumn }) {
    if (column.property === 'colspaOpera') {
      return [1, 2];
    } if (column.property === 'colspaSetting') {
      return [0, 0];
    }
  }
  public rowClassName({ row }: { row: ICloudRow }) {
    return row.isChannel ? 'row-expand-bg' : 'pointer-row';
  }
  /**
   * 跳转agent并筛选出管控区域
   */
  public handleGotoAgent(row: ICloud) {
    MainStore.setSelectedBiz([]);
    this.$router.push({
      name: 'agentStatus',
      params: {
        cloud: {
          id: row.bkCloudId,
          name: row.bkCloudName,
        },
        agentNum: `${row.nodeCount}`,
      },
    });
  }
  public handlePageChange(newPage: number) {
    this.pagination.current = newPage || 1;
    const { current, limit } = this.pagination;
    const start = (current - 1) * limit;
    this.tableData = this.table.data.filter((item, index) => index >= start && index < start + limit);
  }
  public handlePageLimitChange(limit: number) {
    this.pagination.limit = limit || 20;
    this.handlePageChange(1);
  }
  public renderSelectionHeader(h: CreateElement) {
    return h(ColumnCheck, {
      ref: 'customSelectionHeader',
      props: {
        indeterminate: this.indeterminate,
        isAllChecked: this.isAllChecked,
        disabled: !this.checkableRows,
        disabledCheckAll: !this.checkableRowsAll,
      },
      on: {
        change: (value: boolean, type: string) => this.handleCheckAll(value, type),
      },
    });
  }
  public handleRowCheck(arg: boolean[], row: ICloudRow) {
    // 跨页全选采用标记删除法
    if (this.isSelectAllPages) {
      if (!arg[0]) {
        this.excludedRows.push(row);
      } else {
        const index = this.excludedRows.findIndex(item => item.bkCloudId === row.bkCloudId);
        if (index > -1) {
          this.excludedRows.splice(index, 1);
        }
      }
    }
    row.selected = !!arg[0];
  }
  public async handleCheckAll(value: boolean, type: string) {
    if (type === 'current' && !this.checkableRows) return;
    if (type === 'all' && !this.checkableRowsAll) return;
    // 跨页全选
    this.isSelectAllPages = value && type === 'all';
    // 删除标记数组
    this.excludedRows.splice(0, this.excludedRows.length);
    if (this.isSelectAllPages) {
      this.table.data.forEach((row) => {
        if (row.proxyCount) {
          row.selected = value;
        }
      });
    } else {
      this.tableData.forEach((row) => {
        if (row.proxyCount) {
          row.selected = value;
        }
      });
    }
  }
  public async handleCopyIp(type: string) {
    const isIPv4 = !this.$DHCP || !type.includes('v6');
    const ipKey = isIPv4 ? 'innerIp' : 'innerIpv6';
    const associateCloud = type.includes('cloud');
    const isAll = type.includes('all');
    if (!isAll && !this.hasSelectedRows) return;
    if (isAll && !this.checkableRowsAll) return;

    const rows = !isAll
      ? this.table.data.filter(item => item.selected)
      : this.table.data.filter(item => !!item.proxyCount);
    let data: Dictionary[] = [];
    rows.forEach((item) => {
      data.push(...(item.proxies || []));
    });
    data = data.filter(item => item[ipKey]);
    return Promise.resolve(associateCloud
      ? data.map(proxy => (isIPv4
        ? `${proxy.bkCloudId}:${proxy[ipKey]}`
        : `${proxy.bkCloudId}:[${proxy[ipKey]}]`))
      : data.map(item => item[ipKey]));
  }
  // 表格折叠
  public handleExpandChange(row: ICloudRow) {
    if (row.isChannel) return;
    const copyTable = [...this.tableData.filter(item => !item.isChannel)];
    const rowIndex = copyTable.findIndex(item => item.bkCloudId === row.bkCloudId);
    // 手风琴模式
    const expandedRow = this.tableData.find(item => item.expand);
    if (expandedRow) {
      if (expandedRow.bkCloudId === row.bkCloudId) {
        row.expand = false;
      } else {
        expandedRow.expand = false;
        copyTable.splice(rowIndex + 1, 0, ...row.children);
        row.expand = true;
      }
      this.tableData.splice(0, this.tableData.length, ...copyTable);
    } else {
      this.tableData.splice(rowIndex + 1, 0, ...row.children);
      row.expand = true;
    }
  }
  public handleSortChange({ prop, order }: { prop: ISortProp, order: ISortOrder }) {
    this.sortProp = prop;
    this.sortOrder = order;
    this.handleSearch(this.pagination.current);
  }
  public searchClear() {
    this.loading = true;
    this.searchValue = '';
    this.handleValueChange();
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";
@import "@/css/variable.css";

.cloud-manager {
  padding-bottom: 20px;
}
.content-header {
  @mixin layout-flex row, center, space-between;
  .header-btn {
    width: 120px;
  }
  .header-input {
    width: 500px;
  }
  .item-disabled {
    cursor: not-allowed;
    color: #c4c6cc;
    &:hover {
      background: transparent;
      color: #c4c6cc;
    }
  }
}
.content-table {
  .col-svg {
    margin-top: 5px;
    height: 20px;
    margin-right: -15px;
  }
  .col-btn {
    padding: 0;
    .count-icon {
      font-weight: 600;
      &.warning {
        color: #ff9c01;
      }
      &.danger {
        color: #ea3636;
      }
    }
  }
  .text-btn {
    display: inline;
  }
  .auth-inline {
    display: inline;
  }
  .install-proxy {
    cursor: pointer;
    .count-error-text {
      font-weight: 600;
      color: #ea3636;
    }
    &:hover {
      color: #3a84ff;
    }
    &[disabled] {
      color: #dcdee5;
    }
  }
  >>> .col-pl-none .cell {
    padding-left: 0;
  }
  >>> .col-pad-none .cell {
    padding-left: 0;
    padding-right: 0;
  }
  .channel-name {
    display: flex;
    align-items: center;
    .channel-icon {
      color: #c4c6cc;
      margin-right: 4px;
    }
  }
  >>> .row-expand-bg {
    background: #fafbfd;
  }
}
</style>
