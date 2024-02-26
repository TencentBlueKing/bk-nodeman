<template>
  <section class="agent">
    <!--agent操作-->
    <section class="agent-operate mb15">
      <!--agent操作-->
      <div class="agent-operate-left h32">
        <!--安装Agent-->
        <auth-component
          tag="div"
          :authorized="authority.operate"
          :apply-info="[{ action: 'agent_operate' }]">
          <template slot-scope="{ disabled }">
            <bk-button
              v-if="!!selectionCount"
              ext-cls="setup-btn"
              slot="dropdown-trigger"
              theme="primary"
              :disabled="disabled"
              v-test="'install'"
              @click="triggerHandler({ type: 'reinstall' })">
              <span class="icon-down-wrapper">
                <span>{{ $t('安装Agent') }}</span>
              </span>
            </bk-button>
            <bk-dropdown-menu
              v-else
              trigger="click"
              font-size="medium"
              :disabled="disabled"
              @show="handleDropdownShow('isSetupDropdownShow')"
              @hide="handleDropdownHide('isSetupDropdownShow')">
              <bk-button
                ext-cls="setup-btn"
                slot="dropdown-trigger"
                theme="primary"
                :disabled="disabled"
                v-test="'install'">
                <span class="icon-down-wrapper">
                  <span>{{ $t('安装Agent') }}</span>
                  <i :class="['bk-icon icon-angle-down setup-btn-icon', { 'icon-flip': isSetupDropdownShow }]"></i>
                </span>
              </bk-button>
              <ul class="bk-dropdown-list" slot="dropdown-content" v-test="'installUl'">
                <li>
                  <a @click.prevent="triggerHandler({ type: 'setup' })" v-test.common="'moreItem.setup'">
                    {{ $t('普通安装') }}
                  </a>
                </li>
                <li>
                  <a @click.prevent="triggerHandler({ type: 'import' })" v-test.common="'moreItem.import'">
                    {{ $t('Excel导入安装') }}
                  </a>
                </li>
              </ul>
            </bk-dropdown-menu>
          </template>
        </auth-component>

        <!--批量操作-->
        <bk-dropdown-menu
          trigger="click"
          ref="batch"
          font-size="medium"
          class="ml10"
          :disabled="!isSingleHosts || !(indeterminate || isAllChecked)"
          @show="handleDropdownShow('isbatchDropdownShow')"
          @hide="handleDropdownHide('isbatchDropdownShow')">
          <bk-button
            slot="dropdown-trigger"
            :disabled="!isSingleHosts || !(indeterminate || isAllChecked)"
            v-test="'operate'">
            <bk-popover
              placement="bottom"
              :delay="400"
              :disabled="!(!isSingleHosts && (indeterminate || isAllChecked))"
              :content="$t('不同安装方式的Agent不能统一批量操作')">
              <span class="icon-down-wrapper">
                <span>{{ $t('批量') }}</span>
                <i :class="['bk-icon icon-angle-down', { 'icon-flip': isbatchDropdownShow }]"></i>
              </span>
            </bk-popover>
          </bk-button>
          <ul class="bk-dropdown-list" slot="dropdown-content">
            <template v-for="item in operate">
              <li v-if="!item.single" :key="item.id" :class="{ 'disabled': getBatchMenuStaus(item) }">
                <a @click.prevent="!getBatchMenuStaus(item) && triggerHandler({ type: item.id })"
                   v-test.common="`moreItem.${item.id}`">
                  {{ item.name }}
                </a>
              </li>
            </template>
          </ul>
        </bk-dropdown-menu>
        <!--复制IP-->
        <CopyDropdown
          class="ml10"
          :disabled="table.data.length === 0"
          :not-selected="!selectionCount"
          :get-ips="handleCopyIp" />
        <!--选择业务-->
        <!-- <bk-biz-select
          v-model="search.biz"
          class="ml10"
          min-width="240"
          ext-cls="left-select"
          :auto-request="autoRequest"
          :placeholder="$t('全部业务')"
          @change="handleBizChange">
        </bk-biz-select> -->
        <bk-cascade
          class="ml10 mr10 topo-cascade"
          is-remote
          clearable
          check-any-level
          ref="topoSelect"
          v-model="search.topo"
          :placeholder="$t('业务拓扑')"
          :list="topoBizFilterList"
          :remote-method="topoRemotehandler"
          v-test="'bizTopo'"
          @change="topoSelectchange"
          @toggle="handleTopoChange">
          <!-- <template slot="option" slot-scope="{ node }">
            <div v-if="node.type" class="nm-cascade-option" @click.stop="handleLoadCascadeChild(node)">
              {{ node.name }}
            </div>
            <span v-else>{{ node.name }}</span>
          </template> -->
        </bk-cascade>
      </div>
      <!--agent搜索-->
      <div class="agent-operate-right">
        <bk-search-select
          ref="searchSelect"
          ext-cls="right-select"
          :data="searchSelectData"
          :key="searchInputKey"
          v-model="searchSelectValue"
          :show-condition="false"
          :placeholder="$t('agent列表搜索')"
          v-test="'search'"
          @paste.native.capture.prevent="handlePaste"
          @change="handleSearchSelectChange">
        </bk-search-select>
      </div>
    </section>
    <!--agent列表-->
    <section class="agent-content" v-bkloading="{ isLoading: loading }">
      <bk-table
        ref="agentTable"
        :class="`head-customize-table ${ fontSize }`"
        :max-height="tableHeight"
        :cell-class-name="handleCellClass"
        :span-method="colspanHandle"
        :data="table.data"
        @sort-change="handleSort">
        <template #prepend>
          <transition name="tips">
            <div class="selection-tips" v-show="selectionCount">
              <div>
                {{ $t('已选') }}
                <span class="tips-num">{{ selectionCount }}</span>
                {{ $t('条') }},
              </div>
              <bk-button
                ext-cls="tips-btn"
                text
                v-if="!disabledAllChecked && !isSelectedAllPages"
                @click="handleSelectionAll">
                {{ $t('选择所有') }}
                <span class="tips-num">{{ table.pagination.count }}</span>
                {{ $t('条') }}
              </bk-button>
              <bk-button
                ext-cls="tips-btn"
                text
                v-else
                @click="handleClearSelection">
                {{ $t('取消选择所有数据') }}
              </bk-button>
            </div>
          </transition>
        </template>
        <bk-table-column
          key="selection"
          width="65"
          align="center"
          fixed
          :resizable="false"
          :render-header="renderSelectionHeader">
          <template #default="{ row }">
            <auth-component
              tag="div"
              :authorized="row.operate_permission"
              :apply-info="[{
                action: 'agent_operate',
                instance_id: row.bk_biz_id,
                instance_name: row.bk_biz_name
              }]">
              <template slot-scope="{ disabled }">
                <bk-checkbox
                  :value="row.selection"
                  :disabled="row.job_result.status === 'RUNNING' || disabled"
                  @change="handleRowCheck(arguments, row)">
                </bk-checkbox>
              </template>
            </auth-component>
          </template>
        </bk-table-column>
        <NmColumn
          fixed
          key="IP"
          :label="$t('内网IPv4')"
          prop="inner_ip"
          width="125">
          <template #default="{ row }">
            {{ row.inner_ip | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          fixed
          key="inner_ipv6"
          :label="$t('内网IPv6')"
          prop="inner_ipv6"
          :width="innerIPv6Width"
          v-if="filter['inner_ipv6'] && filter['inner_ipv6'].mockChecked">
          <template #default="{ row }">
            {{ row.inner_ipv6 | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          key="bk_host_name"
          :label="$t('主机名')"
          prop="bk_host_name"
          width="140"
          v-if="filter['bk_host_name'].mockChecked">
          <template #default="{ row }">
            {{ row.bk_host_name | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          key="bk_agent_id"
          label="Agent ID"
          prop="bk_agent_id"
          width="260"
          v-if="filter['bk_agent_id'].mockChecked">
          <template #default="{ row }">
            {{ row.bk_agent_id | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          key="bk_host_id"
          label="Host ID"
          prop="bk_host_id"
          width="80"
          v-if="filter['bk_host_id'].mockChecked" />
        <NmColumn
          key="login_ip"
          :label="$t('登录IP')"
          prop="login_ip"
          width="110"
          v-if="filter['login_ip'].mockChecked">
          <template #default="{ row }">
            {{ row.login_ip | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          key="outer_ipv6"
          :label="$t('外网IPv6')"
          prop="outer_ipv6"
          width="110"
          v-if="filter['outer_ipv6'] && filter['outer_ipv6'].mockChecked">
          <template #default="{ row }">
            {{ row.outer_ipv6 | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          key="biz"
          :label="$t('归属业务')"
          prop="bk_biz_name"
          :min-width="columnMinWidth['bk_biz_name']"
          v-if="filter['bk_biz_name'].mockChecked">
        </NmColumn>
        <NmColumn
          key="cloudArea"
          :label="$t('管控区域')"
          :min-width="columnMinWidth['bk_cloud_id']"
          :render-header="renderFilterHeader"
          prop="bk_cloud_id"
          v-if="filter['bk_cloud_id'].mockChecked">
          <template #default="{ row }">
            {{ row.bk_cloud_name | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          key="install_channel_id"
          :label="$t('安装通道')"
          :min-width="columnMinWidth['install_channel_id']"
          :render-header="renderFilterHeader"
          prop="install_channel_id"
          v-if="filter['install_channel_id'].mockChecked">
          <template #default="{ row }">
            {{ row.install_channel_name || $t('默认通道') }}
          </template>
        </NmColumn>
        <NmColumn
          key="system"
          :label="$t('操作系统')"
          prop="os_type"
          :min-width="columnMinWidth['os_type']"
          :render-header="renderFilterHeader"
          v-if="filter['os_type'].mockChecked">
          <template #default="{ row }">
            {{ osMap[row.os_type] | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          key="status"
          :label="$t('Agent状态')"
          prop="status"
          :min-width="columnMinWidth['agent_status']"
          :render-header="renderFilterHeader">
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
        </NmColumn>
        <!-- sortable="custom" -->
        <NmColumn
          key="version"
          :label="$t('Agent版本')"
          prop="version"
          :min-width="columnMinWidth['agent_version']"
          :render-header="renderFilterHeader"
          v-if="filter['agent_version'].mockChecked">
        </NmColumn>
        <NmColumn
          key="is_manual"
          :label="$t('安装方式')"
          prop="is_manual"
          v-if="filter['is_manual'].mockChecked"
          :min-width="columnMinWidth['is_manual']"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            {{ row.is_manual ? $t('手动') : $t('远程') }}
          </template>
        </NmColumn>
        <NmColumn
          key="bt"
          prop="peer_exchange_switch_for_agent"
          :label="$t('BT节点探测')"
          :min-width="columnMinWidth['bt']"
          v-if="filter['bt'].mockChecked">
          <template #default="{ row }">
            <span :class="['tag-switch', { 'tag-enable': row.peer_exchange_switch_for_agent }]">
              {{ row.peer_exchange_switch_for_agent ? $t('启用') : $t('停用')}}
            </span>
          </template>
        </NmColumn>
        <NmColumn
          key="speedLimit"
          prop="bt_speed_limit"
          align="right"
          :label="`${$t('传输限速')}(MB/s)`"
          :min-width="columnMinWidth['speedLimit']"
          v-if="filter['speedLimit'].mockChecked">
          <template #default="{ row }">
            {{ row.bt_speed_limit | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn v-if="filter['speedLimit'].mockChecked" min-width="30" :resizable="false">
        </NmColumn>
        <NmColumn
          key="bt"
          prop="enable_compression"
          :label="$t('数据压缩')"
          :min-width="columnMinWidth['enable_compression']"
          v-if="filter['enable_compression'] && filter['enable_compression'].mockChecked">
          <template #default="{ row }">
            <span :class="['tag-switch', { 'tag-enable': row.enable_compression }]">
              {{ row.enable_compression ? $t('启用') : $t('停用')}}
            </span>
          </template>
        </NmColumn>
        <NmColumn
          key="addressing"
          prop="bk_addressing"
          :label="$t('寻址方式')"
          :min-width="columnMinWidth['bk_addressing']"
          :render-header="renderFilterHeader"
          v-if="filter['bk_addressing'] && filter['bk_addressing'].mockChecked">
          <template #default="{ row }">
            {{ row.bk_addressing === 'dynamic' ? $t('动态') : $t('静态') }}
          </template>
        </NmColumn>
        <NmColumn
          key="created_at"
          :label="$t('安装时间')"
          width="200"
          prop="created_at"
          :resizable="false"
          v-if="filter['created_at'].mockChecked">
          <template #default="{ row }">
            {{ row.created_at | filterTimezone }}
          </template>
        </NmColumn>
        <NmColumn
          key="updated_at"
          :label="$t('更新时间')"
          width="200"
          prop="updated_at"
          :resizable="false"
          v-if="filter['updated_at'].mockChecked">
          <template #default="{ row }">
            {{ row.updated_at | filterTimezone }}
          </template>
        </NmColumn>
        <NmColumn
          key="topology"
          :label="$t('业务拓扑')"
          prop="topology"
          min-width="100"
          :show-overflow-tooltip="false"
          v-if="filter['topology'].mockChecked"
          :resizable="true">
          <template #default="{ row }">
            <template v-if="row.topology.length">
              <div
                v-if="row.topology.length > 1"
                v-bk-tooltips="{
                  content: row.topology.join('<br>'),
                  theme: 'topology-list',
                  delay: [300, 0],
                  placements: 'bottom',
                  boundary: 'window'
                }">
                <span :class="{ 'col-topo': row.topology.length > 1 }">
                  {{ row.topology.join(', ') }}
                </span>
              </div>
              <div v-else v-bk-overflow-tips>{{ row.topology[0] }}</div>
            </template>
            <span v-else>--</span>
          </template>
        </NmColumn>
        <NmColumn
          key="num"
          width="60"
          :resizable="false"
          :show-overflow-tooltip="false"
          v-if="filter['topology'].mockChecked">
          <template #default="{ row }">
            <span
              class="col-num"
              v-if="row.topology.length > 1"
              v-bk-tooltips="{
                content: row.topology.join('<br>'),
                theme: 'light',
                delay: [300, 0],
                placements: 'bottom',
              }">
              {{ `+${row.topology.length}` }}
            </span>
          </template>
        </NmColumn>
        <NmColumn
          key="operate"
          prop="colspaOpera"
          :label="$t('操作')"
          width="150"
          :resizable="false"
          fixed="right">
          <template #default="{ row }">
            <div class="col-operate">
              <auth-component
                v-if="['PENDING', 'RUNNING'].includes(row.job_result.status)"
                class="col-btn ml10"
                tag="div"
                :authorized="row.operate_permission"
                :apply-info="[{
                  action: 'agent_operate',
                  instance_id: row.bk_biz_id,
                  instance_name: row.bk_biz_name
                }]">
                <template slot-scope="{ disabled }">
                  <bk-button text :disabled="disabled" @click="handleGotoLog(row)">
                    <loading-icon></loading-icon>
                    <span class="loading-name" v-bk-tooltips.top="$t('查看任务详情')">
                      {{ row.job_result.current_step || $t('正在运行') }}
                    </span>
                  </bk-button>
                </template>
              </auth-component>
              <auth-component
                v-else
                class="header-left"
                tag="div"
                :authorized="row.operate_permission"
                :apply-info="[{
                  action: 'agent_operate',
                  instance_id: row.bk_biz_id,
                  instance_name: row.bk_biz_name
                }]">
                <template slot-scope="{ disabled }">
                  <bk-button
                    theme="primary"
                    text
                    ext-cls="reinstall"
                    :class="{ 'btn-en': language === 'en' }"
                    :disabled="disabled"
                    v-test="'reload'"
                    @click="handleOperate('reinstall', [row])">
                    {{ row.status === 'not_installed' ? $t('安装') : $t('重装') }}
                  </bk-button>
                  <bk-popover
                    :ref="row['bk_host_id']"
                    theme="light agent-operate"
                    trigger="click"
                    :arrow="false"
                    offset="30, 5"
                    placement="bottom"
                    :disabled="disabled">
                    <bk-button theme="primary" class="ml10" text :disabled="disabled" v-test.common="'more'">
                      {{ $t('更多') }}
                    </bk-button>
                    <template #content>
                      <ul class="dropdown-list">
                        <li
                          v-for="item in operate"
                          v-show="getOperateShow(row, item)"
                          :class="[
                            'list-item',
                            fontSize,
                            { 'disabled': row.status === 'not_installed' && !(['log', 'remove'].includes(item.id)) }
                          ]"
                          :key="item.id"
                          v-test.common="`moreItem.${item.id}`"
                          @click="handleOperate(item.id, [row])">
                          {{ item.name }}
                        </li>
                      </ul>
                    </template>
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
          :resizable="false"
          fixed="right">
        </NmColumn>
        <NmException
          slot="empty"
          :delay="loading"
          :type="tableEmptyType"
          @empty-clear="searchClear"
          @empty-refresh="initAgentListDebounce" />
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
        :selection-count="selectionCount"
        @change="handlePageChange"
        @limit-change="handlePageLimitChange">
      </bk-pagination>
    </section>
    <bk-footer></bk-footer>
  </section>
</template>
<script lang="ts">
import { Component, Watch, Ref, Mixins, Prop } from 'vue-property-decorator';
import { CreateElement } from 'vue';
import { MainStore, AgentStore } from '@/store/index';
import { IBizValue, IBkColumn, ISearchItem, ISortData, ITabelFliter } from '@/types';
import {
  IAgent, IAgentHost, IAgentJob, IAgentTable, IAgentTopo,
  IOperateItem, IAgentSearchIp, IAgentSearch,
} from '@/types/agent/agent-type';

import ColumnSetting from '@/components/common/column-setting.vue';
import ColumnCheck from './components/column-check.vue';
import BkFooter from '@/components/common/footer.vue';
import TableHeaderMixins from '@/components/common/table-header-mixins';
import pollMixin from '@/common/poll-mixin';
import authorityMixin from '@/common/authority-mixin';
import CopyDropdown from '@/components/common/copy-dropdown.vue';
import { debounce, getFilterChildBySelected, searchSelectPaste } from '@/common/util';
import { bus } from '@/common/bus';
import { STORAGE_KEY_COL } from '@/config/storage-key';
import { getDefaultConfig, DHCP_FILTER_KEYS } from '@/config/config';

@Component({
  name: 'agent-list',
  components: {
    BkFooter,
    CopyDropdown,
  },
})
export default class AgentList extends Mixins(pollMixin, TableHeaderMixins, authorityMixin())<IAgent> {
  @Ref('topoSelect') private readonly topoSelect!: any;
  @Ref('batch') private readonly batch!: any;
  @Ref('searchSelect') private readonly searchSelect!: any;
  @Ref('agentTable') private readonly agentTable!: any;

  @Prop({ default: () => [], type: Array }) private readonly ipList!: string[];
  @Prop({ default: () => [], type: Array }) private readonly bk_biz_id!: number[];
  @Prop({ default: () => [], type: Array }) private readonly agent_status!: string[];
  @Prop({ default: () => [], type: Array }) private readonly inner_ip!: string[];

  private table: IAgentTable = {
    // 所有运行主机的数量
    runningCount: 0,
    // 无操作全选的主机
    noPermissionCount: 0,
    // 列表数据
    data: [],
    // 分页
    pagination: {
      current: 1,
      count: 0,
      limit: 50,
      limitList: [50, 100, 200],
    },
  };
  private sortData: ISortData = {
    head: '',
    sort_type: '',
  };
  private loading = true;
  private loadingDelay = false; // 重新拉去过虑条件之后可能需要重置搜素框里的数据
  private searchInputKey = 0;
  // 跨页全选loading
  private checkLoading = false;
  // 列表字段显示配置
  private filter: { [key: string]: ITabelFliter } = {
    inner_ip: {
      checked: true,
      disabled: true,
      mockChecked: true,
      name: window.i18n.t('内网IPv4'),
      id: 'inner_ip',
    },
    login_ip: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('登录IP'),
      id: 'login_ip',
    },
    inner_ipv6: {
      checked: this.$DHCP,
      disabled: this.$DHCP,
      mockChecked: this.$DHCP,
      name: window.i18n.t('内网IPv6'),
      id: 'inner_ipv6',
    },
    outer_ipv6: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('外网IPv6'),
      id: 'outer_ipv6',
    },
    bk_host_name: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('主机名'),
      id: 'bk_host_name',
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
    agent_version: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('Agent版本'),
      id: 'agent_version',
      filter: true,
    },
    agent_status: {
      checked: true,
      disabled: true,
      mockChecked: true,
      name: window.i18n.t('Agent状态'),
      id: 'agent_status',
      filter: true,
    },
    bk_cloud_id: {
      checked: true,
      mockChecked: true,
      disabled: false,
      name: window.i18n.t('管控区域'),
      id: 'bk_cloud_id',
      filter: true,
    },
    install_channel_id: {
      checked: false,
      mockChecked: false,
      disabled: false,
      name: window.i18n.t('安装通道'),
      id: 'install_channel_id',
      filter: true,
    },
    bk_biz_name: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('归属业务'),
      id: 'bk_biz_name',
    },
    topology: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('业务拓扑'),
      id: 'topology',
    },
    os_type: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('操作系统'),
      id: 'os_type',
      filter: true,
    },
    is_manual: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('安装方式'),
      id: 'is_manual',
      filter: true,
    },
    created_at: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('安装时间'),
      id: 'created_at',
    },
    updated_at: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('更新时间'),
      id: 'updated_at',
    },
    bt: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('BT节点探测'),
      id: 'peer_exchange_switch_for_agent',
    },
    speedLimit: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('传输限速'),
      id: 'bt_speed_limit',
    },
    enable_compression: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('数据压缩'),
      id: 'enable_compression',
    },
    bk_addressing: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('寻址方式'),
      id: 'bk_addressing',
      filter: true,
    },
  };
  // 是否显示批量按钮下拉菜单
  private isbatchDropdownShow = false;
  private isSetupDropdownShow = false;
  // 状态map
  private statusMap = {
    running: this.$t('正常'),
    terminated: this.$t('异常'),
    unknown: this.$t('未知'),
  };
  // 批量操作
  private operate: IOperateItem[] = [
    {
      id: 'reinstall',
      name: window.i18n.t('安装重装'),
      disabled: false,
      show: false,
    },
    {
      id: 'upgrade',
      name: window.i18n.t('升级'),
      disabled: false,
      show: true,
    },
    {
      id: 'uninstall',
      name: window.i18n.t('卸载'),
      disabled: false,
      show: true,
    },
    // {
    //   id: 'remove',
    //   name: window.i18n.t('移除'),
    //   disabled: false,
    //   show: true,
    // },
    {
      id: 'reload',
      name: window.i18n.t('重载配置'),
      disabled: false,
      show: true,
    },
    {
      id: 'reboot',
      name: window.i18n.t('重启'),
      disabled: false,
      show: true,
    },
    {
      id: 'log',
      name: window.i18n.t('最新执行日志'),
      disabled: false,
      show: true,
      single: true,
    },
  ];
  // 搜索相关
  private search: {
    topo: number[]
  } = {
    topo: [],
  };
  // 集群/模块 topo
  private topoBizFormat: { [key: string]: IAgentTopo } = {};
  // topo选中的String
  private topoSelectStr = '';
  // 选择的层级
  private topoSelectChild: IAgentTopo[] = [];
  // 搜索防抖
  private initAgentListDebounce: Function = function () {};
  // 是否是跨页全选
  private isSelectedAllPages = false;
  // 跨页全选状态下的数量统计
  private statistics = {
    remote: 0,
    manual: 0,
  };
  // 标记删除数组
  private markDeleteArr: IAgentHost[] = [];
  private localMark = '_agent';
  private operateBiz: IBizValue[] =[]; // 有操作权限的业务
  private cloudAgentNum = 0; // 从管控区域点击跳转过来的主机数量，区分是否因为权限问题看不到主机
  private columnMinWidth: Dictionary = {};

  private get osMap() {
    return MainStore.osMap;
  }
  private get fontSize() {
    return MainStore.fontSize;
  }
  private get language() {
    return MainStore.language;
  }
  private get autoRequest() {
    return !MainStore.permissionSwitch;
  }
  private get bkBizList() {
    return MainStore.bkBizList;
  }
  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  private get innerIPv6Width() {
    const ipv6SortRows: number[] = this.table.data
      .filter(row => !!row.inner_ipv6)
      .map(row => (row.inner_ipv6 as string).length)
      .sort((a, b) => b - a);
    return ipv6SortRows.length ? Math.ceil(ipv6SortRows[0] * 6.9) : 90;
  }
  // 可操作的数据
  private get datasheets() {
    return this.table.data.filter(item => item.job_result.status !== 'RUNNING' && item.operate_permission);
  }
  // 当前列表选择数据
  private get selection() {
    return this.datasheets.filter(item => item.selection);
  }
  // 当前是否是半选状态
  private get indeterminate() {
    if (this.isSelectedAllPages) {
      // 跨页全选半选状态
      return !this.isAllChecked && !!this.markDeleteArr.length;
    }
    return !this.isAllChecked && this.datasheets.some(item => item.selection);
  }
  // 是否全选
  private get isAllChecked() {
    if (this.isSelectedAllPages) {
      // 标记删除的数组为空
      return !this.markDeleteArr.length;
    }
    return this.datasheets.every(item => item.selection);
  }
  // 是否禁用全选checkbox
  private get disabledCheckBox() {
    return !this.datasheets.length;
  }
  // 跨页全选未勾选条数
  private get deleteCount() {
    return this.markDeleteArr.length + this.table.runningCount + this.table.noPermissionCount;
  }
  // 是否禁用跨页全选
  private get disabledAllChecked() {
    return this.table.pagination.count <= this.table.pagination.limit;
  }
  // 已勾选条数
  private get selectionCount() {
    return this.isSelectedAllPages
      ? this.table.pagination.count - this.deleteCount
      : this.selection.length;
  }
  // 是否筛选过一种安装方式 或者 仅存在一种安装方式 那么跨页全选也是可批量操作的
  private get isSingleInstallFilter() {
    const installFilter = this.filterData.find(item => item.id === 'is_manual'
      && item.children && item.children.length === 1);
    return installFilter || this.searchSelectValue.find(item => item.id === 'is_manual' && item.values?.length === 1);
  }
  // 选中机器是否为单种安装类型
  private get isSingleHosts() {
    if (this.isSingleInstallFilter) return true;
    if (!this.selectionCount) return false;
    if (this.isSelectedAllPages) {
      const { manual, remote } = this.statistics;
      return (manual && !remote) || (!manual && remote);
    }
    return new Set(this.selection.map(item => item.is_manual)).size === 1;
  }
  // topo根据业务来展示
  private get topoBizFilterList() {
    const selectLen = this.selectedBiz.length;
    if (selectLen > 1) {
      return this.selectedBiz.map(item => this.topoBizFormat[item]).filter(item => item?.id);
    }
    if (selectLen === 1) {
      const bizIdKey = this.selectedBiz.join('');
      return this.topoBizFormat[bizIdKey] ? this.topoBizFormat[bizIdKey].children || [] : [];
    }
    return this.bkBizList.map(item => this.topoBizFormat[item.bk_biz_id]).filter(item => item?.id);
  }
  private get checkAllPermission() {
    return this.table.data.length
      ? this.table.data.some(item => item.operate_permission)
      : true;
  }
  private get tableHeight() {
    return MainStore.windowHeight - 300 - (MainStore.noticeShow ? 40 : 0);
  }
  private get tableEmptyType() {
    return (this.search.topo.length || this.searchSelectValue.length) ? 'search-empty' : 'empty';
  }

  @Watch('searchSelectValue', { deep: true })
  private handleValueChange() {
    this.table.pagination.current = 1;
    this.initAgentListDebounce();
  }
  @Watch('bkBizList')
  private handleBizListChange() {
    this.initTopoFormat();
  }
  // 存在固定列的情况下展示插入信息需要重新计算表格布局
  @Watch('selectionCount')
  private handleAllCheckedChange() {
    this.$nextTick(() => {
      this.agentTable.doLayout();
    });
  }
  /**
   * 业务变更
   */
  @Watch('selectedBiz')
  private handleBizChange(newValue: number[]) {
    if (newValue.length !== 1) {
      // topo未选择时 清空biz不会触发 cascade组件change事件
      if (this.search.topo.length) {
        this.topoSelect.clearData();
        return false;
      }
    } else {
      const bizIdKey = newValue.join('');
      if (Object.prototype.hasOwnProperty.call(this.topoBizFormat, bizIdKey)
          && this.topoBizFormat[bizIdKey].needLoad) {
        this.topoRemotehandler(this.topoBizFormat[bizIdKey], null);
      }
    }
    this.loadingDelay = true;
    this.loading = true;
    this.getFilterCondition().then(() => {
      const copyValue: ISearchItem[] = [];
      this.searchSelectValue.forEach((item) => {
        const already = this.filterData.find(opt => opt.id === item.id);
        if (already) {
          if (already.children?.length) {
            copyValue.push({
              ...item,
              values: item.values?.filter(opt => already.children?.find(child => child.id === opt.id)),
            });
          } else {
            copyValue.push(item);
          }
        }
      });
      this.handleSearchSelectChange(copyValue);
      this.loadingDelay = false;
      this.table.pagination.current = 1;
      this.initAgentListDebounce();
    });
  }

  private created() {
    this.initRouterQuery();
    this.computedColumnWidth();
  }
  private mounted() {
    this.initAgentListDebounce = debounce(300, this.initAgentList);
    this.handleInit();
  }

  private async getFilterCondition() {
    const param = { category: 'host' };
    if (this.selectedBiz.length) {
      Object.assign(param, { bk_biz_ids: this.selectedBiz });
    }
    const optSearchKeys = ['version', 'bk_cloud_id'];
    const data = await AgentStore.getFilterCondition(param);
    this.filterData.splice(0, this.filterData.length, ...data.map(item => (optSearchKeys.includes(item.id)
      ? ({ ...item, showCheckAll: true, showSearch: true })
      : item)));
    return data;
  }

  private async handleInit() {
    this.initCustomColStatus();
    const { cloud, agentNum } = this.$route.params;
    if (!cloud && !this.agent_status.length) {
      this.initAgentListDebounce();
    }
    if (agentNum) {
      this.cloudAgentNum = (agentNum as any);
    }
    if (this.bkBizList) {
      this.initTopoFormat();
    }
  }
  private initRouterQuery() {
    // this.search.biz = this.bk_biz_id.length ? [...this.bk_biz_id] : this.selectedBiz;
    const searchParams: ISearchItem[] = [];
    const { cloud } = this.$route.params;
    this.getFilterCondition().then((data) => {
      if (cloud) {
        searchParams.push({
          name: this.filter.bk_cloud_id.name,
          id: 'bk_cloud_id',
          values: [cloud as any],
        });
      }
      if (this.inner_ip.length || (this.ipList && this.ipList.length)) {
        const ipList = this.inner_ip.length ? this.inner_ip : this.ipList;
        searchParams.push({
          id: 'inner_ip',
          name: 'IP',
          values: ipList.map(item => ({ id: item, name: item, checked: false })),
        });
      }
      if (this.agent_status.length) {
        const statusFilter = data.find(item => item.id === 'status');
        if (statusFilter?.children) {
          const statusArr = this.agent_status.map((status) => {
            const childFilter = (statusFilter.children || []).find(item => item.id === status);
            return {
              checked: true,
              id: status,
              name: childFilter?.name || status,
            };
          });
          searchParams.push({
            id: 'agent_status',
            name: this.filter.agent_status.name,
            values: statusArr,
          });
        }
      }
      if (searchParams.length) {
        this.searchSelectValue.push(...searchParams);
        this.searchInputKey += 1;
      }
    });
  }

  public computedColumnWidth() {
    const widthMap: { [key: string]: number } = {};
    Object.keys(this.filter).reduce((obj, key) => {
      const column = this.filter[key];
      const config = { filter: column.filter };
      let name = this.filter[key]?.name || '';
      if (key === 'speedLimit') {
        name = `${name}(MB/s)`;
      }
      obj[key] = this.$textTool.getHeadWidth(name, config);
      return obj;
    }, widthMap);
    this.columnMinWidth = widthMap;
  }
  private initCustomColStatus() {
    if (!this.$DHCP) {
      const columnsFilter: Dictionary = {};
      Object.keys(this.filter).forEach((key) => {
        if (!DHCP_FILTER_KEYS.includes(key)) {
          columnsFilter[key] = this.filter[key];
        }
      });
      this.$set(this, 'filter', columnsFilter);
    }
    const data = this.handleGetStorage();
    if (data && Object.keys(data).length) {
      Object.keys(this.filter).forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(data, key)) {
          this.filter[key].mockChecked = !!data[key];
          this.filter[key].checked = !!data[key];
        }
      });
    }
  }
  private initTopoFormat() {
    const bizFormat: IAgent = {};
    this.bkBizList.forEach((item) => {
      bizFormat[item.bk_biz_id] = {
        id: item.bk_biz_id,
        name: item.bk_biz_name,
        path: item.bk_biz_name,
        type: 'biz',
        disabled: item.disabled || false,
        children: [],
        needLoad: true,
      };
    });
    this.topoBizFormat = bizFormat;
    if (this.selectedBiz.length === 1) {
      const bizIdKey = this.selectedBiz.join('');
      if (Object.prototype.hasOwnProperty.call(this.topoBizFormat, bizIdKey)
          && this.topoBizFormat[bizIdKey].needLoad) {
        this.topoRemotehandler(this.topoBizFormat[bizIdKey], null);
      }
    }
  }
  public searchClear() {
    this.loading = true;
    this.topoSelect.clearData();
    this.searchSelectValue = [];
    this.handleSearchSelectChange([]);
  }
  /**
   * 初始化agent列表
   * @param {Boolean} spreadChecked 是否是跨页操作
   */
  private async initAgentList(spreadChecked = false) {
    if (this.loadingDelay) return;
    this.loading = true;
    if (!spreadChecked) {
      this.isSelectedAllPages = false;
      this.markDeleteArr.splice(0, this.markDeleteArr.length);
      this.handleClearSelection(); // 防止二次勾选时还是处于跨页全选状态
    }

    this.runingQueue.splice(0, this.runingQueue.length);
    this.timer && clearTimeout(this.timer);
    this.timer = null;

    const extraData = ['job_result', 'identity_info'];
    if (this.filter.topology.mockChecked) {
      extraData.push('topology');
    }
    const params = this.getSearchCondition(extraData);
    const data = await AgentStore.getHostList(params);
    this.table.data = data.list.map((item: IAgentHost) => {
      // 跨页勾选
      item.selection = this.isSelectedAllPages
      && this.markDeleteArr.findIndex(v => v.bk_host_id === item.bk_host_id) === -1;
      // 轮询任务队列
      if (item.job_result.status && item.job_result.status === 'RUNNING') {
        this.runingQueue.push(item.bk_host_id);
      }
      return item;
    });
    this.table.pagination.count = data.total;
    this.loading = false;
    if (this.cloudAgentNum) {
      if (!data.isFaied && this.cloudAgentNum > data.total) {
        this.$bkMessage({
          theme: 'primary',
          message: this.$t('无法查看完整Agent信息'),
          ellipsisLine: 2,
        });
      }
      this.cloudAgentNum = 0;
    }
  }
  /**
   * 运行轮询任务
   */
  public async handlePollData() {
    const data = await AgentStore.getHostList({
      page: 1,
      pagesize: this.runingQueue.length,
      bk_host_id: this.runingQueue,
      extra_data: ['job_result', 'identity_info'],
    });
    this.handleChangeStatus(data);
  }
  /**
   * 变更轮询回来的数据状态
   * @param {Object} data
   */
  private handleChangeStatus(data: { list: IAgentHost[] }) {
    data.list.forEach((item: IAgentHost) => {
      const index = this.table.data.findIndex(row => row.bk_host_id === item.bk_host_id);
      if (index > -1) {
        if (item.job_result.status !== 'RUNNING') {
          const i = this.runingQueue.findIndex(id => id === item.bk_host_id);
          this.runingQueue.splice(i, 1);
        }
        this.$set(this.table.data, index, item);
      }
    });
  }
  private getCommonCondition() {
    const params: IAgent = {
      conditions: [],
    };
    if (this.sortData.head && this.sortData.sort_type) {
      params.sort = Object.assign({}, this.sortData);
    }
    if (this.selectedBiz.length && this.selectedBiz.length !== this.bkBizList.length) {
      params.bk_biz_id = [...this.selectedBiz];
    }
    // 其他搜索条件
    this.searchSelectValue.forEach((item) => {
      if (Array.isArray(item.values)) {
        const value: string[] = [];
        item.values.forEach((child) => {
          value.push(...getFilterChildBySelected(item.id, child.name, this.filterData).map(item => item.id));
        });
        params.conditions.push({ key: item.id, value });
      } else {
        params.conditions.push({ key: 'query', value: item.name });
      }
    });
    /**
     * 非 set|module 的类型为 自定义层级
     * 自定义层级下一定为 set | 自定义层级,  module上层一定为set
     * 选中为自定义层级需要拿到其下所有的set
     * 拿到module类型 就不需要 set类型的选中值
     * 全选或多选业务之后顶层一定是biz
     * 入手点还是最后一个选中的子节点
     */
    if (this.search.topo.length) {
      const len = this.topoSelectChild.length;
      const lastSelect = this.topoSelectChild[len - 1];
      if (lastSelect.type !== 'biz') {
        if (params.bk_biz_id) {
          delete params.bk_biz_id;
        }
        const value: IAgent = {
          bk_biz_id: this.selectedBiz.length === 1 ? this.selectedBiz[0] : this.search.topo[0],
        };
        if (lastSelect.type === 'set') {
          value.bk_set_ids = [lastSelect.id];
        } else if (lastSelect.type === 'module') {
          // module的上级必定为set
          // const penultSelect = this.topoSelectChild[len - 2];
          // value.bk_set_ids = [penultSelect.id];
          value.bk_module_ids = [lastSelect.id];
        } else {
          value.bk_set_ids = this.getTopoSetDeep(lastSelect, []);
        }
        params.conditions.push({
          key: 'topology',
          value,
        });
      } else {
        params.bk_biz_id = [lastSelect.id];
      }
    }
    return params;
  }
  /**
   * 找到 自定义层级 下的所有 set
   */
  private getTopoSetDeep(topoItem: IAgentTopo, setArr: number[]): number[] {
    if (topoItem.type === 'set') {
      setArr.push(topoItem.id);
    } else if (topoItem.type !== 'module' && topoItem.type !== 'biz') {
      if (topoItem.children?.length) {
        topoItem.children.forEach((item) => {
          this.getTopoSetDeep(item, setArr);
        });
      }
    }
    return setArr;
  }
  /**
   * 获取主机列表当前所有查询条件
   */
  private getSearchCondition(extraData: string[] = []): IAgentSearch {
    const params = {
      page: this.table.pagination.current,
      pagesize: this.table.pagination.limit,
      extra_data: extraData,
    };

    return Object.assign(params, this.getCommonCondition());
  }
  /**
   * 标记删除法查询参数
   */
  private getExcludeHostCondition(extraData: string[] = []) {
    const params = {
      pagesize: -1,
      exclude_hosts: this.markDeleteArr.map(item => item.bk_host_id),
      extra_data: extraData,
    };

    return Object.assign(params, this.getCommonCondition());
  }

  /**
   * 获取删除主机信息的查询条件
   */
  private getDeleteHostCondition(data: IAgentHost[] = []) {
    const params: IAgent = {
      is_proxy: false,
    };
    if (this.isSelectedAllPages) {
      params.exclude_hosts = this.markDeleteArr.map(item => item.bk_host_id);
    } else {
      params.bk_host_id = data.length
        ? data.map(item => item.bk_host_id)
        : this.selection.map(item => item.bk_host_id);
    }

    return Object.assign(params, this.getCommonCondition());
  }
  /**
   * 获取重启主机的查询条件
   */
  private getOperateHostCondition(data: IAgentHost[] = [], operateType: string) {
    const params: IAgent = {
      job_type: operateType,
    };
    if (this.isSelectedAllPages) {
      params.exclude_hosts = this.markDeleteArr.map(item => item.bk_host_id);
    } else {
      params.bk_host_id = data.length
        ? data.map((item: IAgentHost) => item.bk_host_id)
        : this.selection.map(item => item.bk_host_id);
    }

    return Object.assign(params, this.getCommonCondition());
  }
  /**
   * 拉取拓扑
   */
  private handleTopoChange(toggle: boolean) {
    if (toggle) {
      this.topoSelectStr = this.search.topo.join(',');
    } else {
      if (this.topoSelectStr !== this.search.topo.join(',')) {
        this.topoSelectStr = '';
        this.table.pagination.current = 1;
        this.initAgentListDebounce();
      }
    }
  }
  /**
   * 拿到最后一次选择的层级
   */
  private topoSelectchange(newValue: number[], oldValue: number[], selectList: IAgentTopo[]) {
    this.topoSelectChild = selectList;
    // 组件bug，clear事件并未派发出来
    if (!newValue.length) {
      this.table.pagination.current = 1;
      this.initAgentListDebounce();
    }
  }
  private async topoRemotehandler(item: IAgentTopo, resolve: any) {
    if (item.needLoad && !item.isLoading) {
      this.$set(item, 'isLoading', true);
      const res = await MainStore.getBizTopo({ bk_biz_id: item.id });
      if (res) {
        if (!Array.isArray(res)) {
          return [];
        }
        item.needLoad = false;
        item.children = res;
        const bizIdKey = item.id;
        if (Object.prototype.hasOwnProperty.call(this.topoBizFormat, bizIdKey)) {
          this.topoBizFormat[bizIdKey].children = res;
          this.topoBizFormat[bizIdKey].needLoad = false;
        }
      }
    }
    // resolve更新children, 数据放store会有bug
    if (resolve) {
      resolve(item);
    }
  }
  /**
   * 安装 Agent（普通安装）
   */
  private handleSetupAgent() {
    this.$router.push({ name: 'agentSetup' });
  }
  /**
   * 安装 Agent（Excel 导入）
   */
  private handleImportAgent() {
    this.$router.push({ name: 'agentImport' });
  }
  private handlePageChange(page?: number) {
    this.table.pagination.current = page || 1;
    this.initAgentListDebounce(true);
  }
  private handlePageLimitChange(limit: number) {
    this.table.pagination.current = 1;
    this.table.pagination.limit = limit;
    this.initAgentListDebounce(true);
  }
  /**
   * 自定义字段显示列
   * @param {createElement 函数} h 渲染函数
   */
  private renderHeader(h: CreateElement) {
    return h(ColumnSetting, {
      props: {
        'filter-head': true,
        localMark: this.localMark,
        value: this.filter,
      },
      on: {
        update: (data: { [key: string]: ITabelFliter }) => this.handleColumnUpdate(data),
      },
    });
  }
  /**
   * 字段显示列确认事件
   */
  private handleColumnUpdate(data: { [key: string]: ITabelFliter }) {
    const originTopoChecked = this.filter.topology.mockChecked;
    const currentTopoChecked = data.topology.mockChecked;
    this.filter = data;
    if (currentTopoChecked && currentTopoChecked !== originTopoChecked) {
      this.initAgentListDebounce();
    }
    this.$forceUpdate();
  }
  private handleDropdownShow(value: string) {
    this[value] = true;
  }
  private handleDropdownHide(value: string) {
    this[value] = false;
  }
  /**
   * 复制 IP
   */
  private async handleCopyIp(type: string) {
    const key = this.$DHCP && type.includes('v6') ? 'inner_ipv6' : 'inner_ip';
    let list = this.selection.filter(item => item[key]).map(item => item[key]);
    const isAll = type.includes('all');
    if (isAll || this.isSelectedAllPages) {
      const params: IAgent = {
        pagesize: -1,
        only_ip: true,
        return_field: key,
      };
      if (this.isSelectedAllPages && !isAll && this.markDeleteArr.length) {
        params.exclude_hosts = this.markDeleteArr.map(item => item.bk_host_id);
      }
      const data = await AgentStore.getHostIp(Object.assign(params, this.getCommonCondition()) as IAgentSearchIp);
      list = data.list;
    }
    return Promise.resolve(list);
  }

  /**
   * 操作
   * @param {Object} item
   */
  private triggerHandler(item: { type: string, disabled?: boolean }) {
    if (item.disabled) return;
    const data = this.isSelectedAllPages ? this.markDeleteArr : this.selection;
    switch (item.type) {
      // 批量重启 批量重装 批量重载配置 批量卸载 批量升级
      case 'reboot':
      case 'reinstall':
      case 'reload':
      case 'uninstall':
      case 'upgrade':
      case 'remove':
        this.handleOperate(item.type, data, true);
        break;
        // 普通安装
      case 'setup':
        this.handleSetupAgent();
        break;
        // Excel 导入
      case 'import':
        this.handleImportAgent();
        break;
    }
    this.batch.hide();
  }
  /**
   * row勾选事件
   */
  private handleRowCheck(arg: boolean[], row: IAgentHost) {
    // 跨页全选采用标记删除法
    if (this.isSelectedAllPages) {
      if (!arg[0]) {
        this.markDeleteArr.push(row);
        this.setStatistics(row, 'remove');
      } else {
        const index = this.markDeleteArr.findIndex(item => item.bk_host_id === row.bk_host_id);
        if (index > -1) {
          this.markDeleteArr.splice(index, 1);
          this.setStatistics(row);
        }
      }
    }
    this.$set(row, 'selection', arg[0]);
  }
  private setStatistics(row: IAgentHost, operate: 'add' | 'remove' = 'add')  {
    const  type = row.is_manual ? 'manual' : 'remote';
    if (operate === 'add') {
      this.statistics[type] += 1;
    } else {
      this.statistics[type] -= 1;
    }
  }
  /**
   * 自定义selection表头
   */
  private renderSelectionHeader(h: CreateElement) {
    return h(ColumnCheck, {
      ref: 'customSelectionHeader',
      props: {
        indeterminate: this.indeterminate,
        isAllChecked: this.isAllChecked,
        loading: this.checkLoading,
        disabled: this.disabledCheckBox,
        disabledCheckAll: this.disabledAllChecked,
        action: 'agent_operate',
        checkAllPermission: this.checkAllPermission,
      },
      on: {
        change: (value: boolean, type: string) => this.handleCheckAll(value, type),
      },
    });
  }
  /**
   * 表头勾选事件
   * @param {Boolean} value 全选 or 取消全选
   * @param {String} type 当前页全选 or 跨页全选
   */
  private async handleCheckAll(value: boolean, type: string) {
    if (type === 'current' && this.disabledCheckBox) return;
    // 跨页全选
    this.isSelectedAllPages = value && type === 'all';
    if (!value) {
      this.statistics.remote = 0;
      this.statistics.manual = 0;
    }
    // 删除标记数组
    this.markDeleteArr.splice(0, this.markDeleteArr.length);
    if (this.isSelectedAllPages) {
      this.checkLoading = true;
      const params = Object.assign({
        pagesize: -1,
        running_count: true,
      }, this.getCommonCondition());
      const {
        manual_statistics: statistics,
        running_count: runningCount,
        no_permission_count: noPermissionCount,
      } = await AgentStore.getRunningHost(params);
      this.statistics.remote = statistics.false;
      this.statistics.manual = statistics.true;
      this.table.runningCount = runningCount;
      this.table.noPermissionCount = noPermissionCount;
      this.checkLoading = false;
    }
    this.table.data.forEach((item) => {
      if (item.job_result.status !== 'RUNNING' && item.operate_permission) {
        this.$set(item, 'selection', value);
      }
    });
  }
  /**
   * Agent操作
   * @param {String} type 操作类型
   * @param {Array} data agent数据
   * @param {Boolean} batch 是否是批量操作
   *
   * 重装都需要经过编辑页面 *****
   * Linux升级走job不需要编辑，windows升级需要编辑不走job， 混合走编辑 *****
   * Linux、window卸载都不需要经过编辑页面 *****
   */
  private handleOperate(type: string, data: IAgentHost[], batch = false) {
    if (!batch && data[0].status === 'not_installed' && !(['log', 'reinstall', 'remove'].includes(type))) {
      return;
    }
    if (!batch && this.$refs[data[0].bk_host_id]) {
      (this.$refs[data[0].bk_host_id] as any).instance.hide();
    }

    let jobType = '';

    switch (type) {
      // 重启
      case 'reboot':
        this.handleOperatetHost(data, batch, 'RESTART_AGENT');
        break;
        // 移除
      case 'remove':
        this.handleOperatetHost(data, batch, 'REMOVE_AGENT');
        break;
        // 重装
      case 'reinstall':
        // title = this.$t('重装Agent')
        jobType = 'REINSTALL_AGENT';
        break;
        // 重载 只取其中一部分数据
      case 'reload':
        jobType = 'RELOAD_AGENT';
        break;
        // 卸载
      case 'uninstall':
        jobType = 'UNINSTALL_AGENT';
        break;
        // 升级
      case 'upgrade':
        this.handleOperatetHost(data, batch, 'UPGRADE_AGENT');
        break;
        // 日志详情
      case 'log':
        this.handleGotoLog(data[0]);
        break;
    }
    if (!jobType) return;

    this.$router.push({
      name: 'agentEdit',
      params: {
        tableData: data.map(({ identity_info = {}, ...item }) => ({
        // tableData: data.map(({ identity_info = {}, inner_ip, inner_ipv6, ...item }) => ({
          ...item,
          ...identity_info,
          // inner_ip: inner_ip || inner_ipv6,
          // eslint-disable-next-line max-len
          install_channel_id: ((item.bk_cloud_id !== window.PROJECT_CONFIG.DEFAULT_CLOUD && item.install_channel_id === -1) || !item.install_channel_id)
            ? 'default'
            : item.install_channel_id,
          port: item.os_type === 'WINDOWS' && (!identity_info.port || item.bk_cloud_id !== window.PROJECT_CONFIG.DEFAULT_CLOUD)
            ? getDefaultConfig(item.os_type, 'port', 445)  : identity_info.port,
        })),
        type: jobType,
        // true：跨页全选（tableData表示标记删除的数据） false：非跨页全选（tableData表示编辑的数据）
        isSelectedAllPages: batch && this.isSelectedAllPages,
        condition: this.getExcludeHostCondition(['identity_info']),
      },
    });
  }
  /**
   * 跳转日志详情
   */
  private handleGotoLog(data: IAgentHost) {
    if (!data || !data.job_result) return;
    this.$router.push({
      name: 'taskLog',
      params: {
        instanceId: data.job_result.instance_id,
        taskId: data.job_result.job_id,
      },
    });
  }
  /**
   * 重启Host
   * @param {Array} data
   */
  private handleOperatetHost(data: IAgentHost[], batch: boolean, operateType: string) {
    const titleObj = {
      firstIp: batch ? this.selection[0].inner_ip : data[0].inner_ip,
      num: batch ? this.selectionCount : data.length,
    };
    const operateJob = async (data: IAgentHost[]) => {
      this.loading = true;
      const params = this.getOperateHostCondition(data, operateType) as IAgentJob;
      const result = await AgentStore.operateJob(params);
      this.loading = false;
      if (result.job_id) {
        this.$router.push({ name: 'taskDetail', params: { taskId: result.job_id, routerBackName: 'taskList' } });
      }
    };
    let type = '';
    switch (operateType) {
      // 重启
      case 'RESTART_AGENT':
        type = window.i18n.t('重启lower');
        break;
        // 升级
      case 'UPGRADE_AGENT':
        type = window.i18n.t('升级lower');
        break;
      case 'REMOVE_AGENT':
        type = window.i18n.t('移除lower');
        break;
    }
    this.$bkInfo({
      title: batch
        ? this.$t('请确认是否批量操作', { type })
        : this.$t('请确认是否操作', { type }),
      subTitle: batch
        ? this.$t('批量确认操作提示', {
          ip: titleObj.firstIp,
          num: titleObj.num,
          type,
          suffix: operateType === 'UPGRADE_AGENT' ? this.$t('到最新版本') : '' })
        : this.$t('单条确认操作提示', {
          ip: titleObj.firstIp,
          type,
          suffix: operateType === 'UPGRADE_AGENT' ? this.$t('到最新版本') : '',
        }),
      extCls: 'wrap-title',
      confirmFn: () => {
        if (operateType === 'REMOVE_AGENT') {
          this.handleRemoveHost(data);
        } else {
          operateJob(data);
        }
      },
    });
  }
  /**
   * 移除Agent
   * @param {Array} data
   */
  private async handleRemoveHost(data: IAgentHost[] = []) {
    this.loading = true;
    const param = this.getDeleteHostCondition(data) as IAgentJob;
    const result = await AgentStore.removeHost(param);
    if (result) {
      this.$bkMessage({
        theme: 'success',
        message: result.fail && result.fail.length
          ? this.$t('删除完成提示', { success: result.success, fail: result.fail })
          : this.$t('删除成功'),
      });
      this.initAgentListDebounce();
    } else {
      this.loading = false;
    }
  }
  /**
   * 跨页全选
   */
  private handleSelectionAll() {
    bus.$emit('checked-all-agent');
  }
  /**
   * 取消跨页全选
   */
  private handleClearSelection() {
    bus.$emit('unchecked-all-agent');
  }
  /**
   * 获取存储信息
   */
  private handleGetStorage(): IAgent {
    let data = {};
    try {
      data = JSON.parse(window.localStorage.getItem(this.localMark + STORAGE_KEY_COL) || '');
    } catch (_) {
      data = {};
    }
    return data;
  }
  /**
   * search select复制逻辑
   */
  private handlePaste(e: { target: EventTarget, clipboardData: any, originalEvent?: any }) {
    searchSelectPaste({
      e,
      selectedValue: this.searchSelectValue,
      filterData: this.filterData,
      selectRef: this.searchSelect,
      pushFn: this.handlePushValue,
      changeFn: this.handleValueChange,
      areaFilter: true,
    });
  }
  /**
   * agent 版本排序
   */
  private handleSort({ prop, order }: { prop: string, order: string }) {
    Object.assign(this.sortData, {
      head: prop,
      sort_type: order === 'ascending' ? 'ASC' : 'DEC',
    });
    this.handlePageChange();
  }
  /**
   * 单元格样式
   */
  private handleCellClass({ column }: { column: IBkColumn }) {
    if (column.property && column.property === 'topology') {
      return 'col-topology';
    }
  }
  /**
   * 当前操作项是否显示
   */
  private getOperateShow(row: IAgentHost, config: IOperateItem) {
    if (config.id === 'log' && (!row.job_result || !row.job_result.job_id)) {
      return false;
    }
    return config.show;
  }
  /**
   * 合并最后两列
   */
  private colspanHandle({ column }: { column: IBkColumn }) {
    if (column.property === 'colspaOpera') {
      return [1, 2];
    } if (column.property === 'colspaSetting') {
      return [0, 0];
    }
  }
  private getBatchMenuStaus(item: IOperateItem) {
    return !this.isSelectedAllPages && !(['reinstall', 'log', 'remove'].includes(item.id))
      ? this.selection.every(row => row.status === 'not_installed')
      : false;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";
@import "@/css/transition.css";

@define-mixin col-row-status $color {
  margin-right: 10px;
  margin-top: -1px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: $color;
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
  max-height: none;
  li {
    cursor: pointer;
    &.disabled a {
      color: #c4c6cc;
      cursor: not-allowed;
    }
  }
}
>>> .bk-table tr:hover {
  .col-num {
    background: #dcdee5;
  }
}
>>> .icon-down-wrapper {
  position: relative;
  left: 3px;
}
.agent {
  padding-bottom: 82px;
  &-operate {
    @mixin layout-flex row, center, space-between;
    &-left {
      @mixin layout-flex row;
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
        min-width: 136px;
        transition: none;
        .setup-btn-icon {
          transition: transform .2s ease;
        }
        &[disabled],
        >>> &[disabled] * {
          /* stylelint-disable-next-line declaration-no-important */
          border-color: #dcdee5 !important;

          /* stylelint-disable-next-line declaration-no-important */
          color: #fff!important;

          /* stylelint-disable-next-line declaration-no-important */
          background-color: #dcdee5!important;
        }
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
        width: 240px;
        background: #fff;
      }
      .topo-cascade {
        width: 240px;
        height: 32px;
        background: #fff;
        >>> .bk-tooltip-ref {
          width: 100%;
        }
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
    .col-operate {
      .reinstall {
        padding: 0;
        min-width: 24px;
        &.btn-en {
          min-width: 50px;
          text-align: left;
        }
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
</style>
