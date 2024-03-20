<template>
  <section>
    <div class="flex">
      <auth-component
        tag="div"
        :authorized="!!proxyOperateList.length"
        :apply-info="[{ action: 'proxy_operate' }]">
        <template slot-scope="{ disabled }">
          <bk-button
            v-test="'install'"
            theme="primary"
            class="content-btn nodeman-primary-btn"
            :disabled="disabled"
            @click="handleRouterPush('setupCloudManager', { type: 'create', id })">
            {{ $t('安装Proxy') }}
          </bk-button>
        </template>
      </auth-component>
      <bk-popover>
        <CopyDropdown
          class="ml10"
          :list="copyMenu"
          :disabled="!proxyData.length"
          :get-ips="handleCopyIp" />
        <template #content>
          {{ $t('复制ProxyIP') }}
        </template>
      </bk-popover>
    </div>

    <div v-bkloading="{ isLoading: loadingProxy || loading }">
      <bk-table
        v-test="'proxyTable'"
        :class="`head-customize-table ${ fontSize }`" :data="proxyData" :span-method="colspanHandle">
        <NmColumn :label="$t('内网IPv4')" width="125">
          <template #default="{ row }">
            <bk-button v-if="row.inner_ip" v-test="'view'" text @click="handleViewProxy(row, false)" class="row-btn">
              {{ row.inner_ip }}
            </bk-button>
            <template v-else>{{ row.inner_ip | filterEmpty }}</template>
          </template>
        </NmColumn>
        <NmColumn
          v-if="filter['inner_ipv6'] && filter['inner_ipv6'].mockChecked"
          :width="innerIPv6Width"
          :label="$t('内网IPv6')">
          <template #default="{ row }">
            <bk-button v-if="row.inner_ipv6" v-test="'view'" text @click="handleViewProxy(row, false)" class="row-btn">
              {{ row.inner_ipv6 }}
            </bk-button>
            <template v-else>{{ row.inner_ipv6 | filterEmpty }}</template>
          </template>
        </NmColumn>
        <NmColumn
          :label="$t('出口IP')"
          v-if="filter['outer_ip'].mockChecked"
          :render-header="renderTipHeader"
          width="125">
          <template #default="{ row }">
            <span>{{ row.outer_ip | filterEmpty }}</span>
          </template>
        </NmColumn>
        <NmColumn
          key="login_ip"
          :label="$t('登录IP')"
          prop="login_ip"
          v-if="filter['login_ip'].mockChecked"
          width="125">
          <template #default="{ row }">
            {{ row.login_ip | filterEmpty }}
          </template>
        </NmColumn>
        <NmColumn
          :label="$t('归属业务')"
          prop="bk_biz_name"
          min-width="130"
          v-if="filter['bk_biz_name'].mockChecked">
          <template #default="{ row }">
            <span>{{ row.bk_biz_name | filterEmpty }}</span>
          </template>
        </NmColumn>
        <NmColumn
          :label="$t('Proxy状态')"
          prop="status"
          v-if="filter['proxy_status'].mockChecked"
          :min-width="columnMinWidth['proxy_status']">
          <template #default="{ row }">
            <div class="col-status" v-if="statusMap[row.status]">
              <span :class="'status-mark status-' + row.status"></span>
              <span>{{ statusMap[row.status] }}</span>
            </div>
            <div class="col-status" v-else>
              <span class="status-mark status-unknown"></span>
              <span>{{ $t('未知') }}</span>
            </div>
          </template>
        </NmColumn>
        <NmColumn
          :label="$t('密码/密钥')"
          prop="re_certification"
          v-if="filter['re_certification'].mockChecked"
          :min-width="columnMinWidth['re_certification']">
          <template #default="{ row }">
            <span :class="['tag-switch', { 'tag-enable': !row.re_certification }]">
              {{ row.re_certification ? $t('过期') : $t('有效') }}
            </span>
          </template>
        </NmColumn>
        <NmColumn
          :label="$t('Proxy版本')"
          prop="version"
          v-if="filter['proxy_version'].mockChecked"
          :min-width="columnMinWidth['proxy_version']">
          <template #default="{ row }">
            <span>{{ row.version | filterEmpty }}</span>
          </template>
        </NmColumn>
        <NmColumn
          :label="$t('Agent数量')"
          prop="pagent_count"
          v-if="filter['pagent_count'].mockChecked"
          :min-width="columnMinWidth['pagent_count']">
          <template #default="{ row }">
            <span
              class="link-pointer"
              v-if="row.pagent_count"
              @click="handleFilterAgent">
              {{ row.pagent_count }}
            </span>
            <span v-else>0</span>
          </template>
        </NmColumn>
        <NmColumn :label="$t('安装方式')" prop="is_manual" v-if="filter['is_manual'].mockChecked" min-width="105">
          <template #default="{ row }">
            {{ row.is_manual ? $t('手动') : $t('远程') }}
          </template>
        </NmColumn>
        <NmColumn
          key="bt"
          prop="peer_exchange_switch_for_agent"
          width="110"
          :label="$t('BT节点探测')"
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
          width="130"
          align="right"
          :label="`${$t('传输限速')}(MB/s)`"
          v-if="filter['speedLimit'].mockChecked">
          <template #default="{ row }">
            {{ row.bt_speed_limit | filterEmpty }}
          </template>
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
          v-if="filter['speedLimit'].mockChecked"
          min-width="20"
          :resizable="false">
        </NmColumn>
        <NmColumn
          :label="$t('安装时间')"
          width="200"
          prop="created_at"
          :resizable="false"
          v-if="filter['created_at'].mockChecked">
          <template #default="{ row }">
            {{ row.created_at | filterTimezone }}
          </template>
        </NmColumn>

        <bk-table-column prop="colspanOperate" :label="$t('操作')" width="148" :resizable="false" fixed="right">
          <template #default="{ row }">
            <div class="col-operate">
              <auth-component
                tag="div"
                v-if="['PENDING', 'RUNNING'].includes(row.job_result.status)"
                :authorized="row.permissions && row.permissions.operate"
                :apply-info="[{
                  action: 'proxy_operate',
                  instance_id: row.bk_biz_id,
                  instance_name: row.bk_biz_name
                }]">
                <template #default="{ disabled }">
                  <bk-button :disabled="disabled" text @click="handleGotoLog(row)">
                    <loading-icon vertical="text-bottom"></loading-icon>
                    <span
                      class="loading-name"
                      v-bk-tooltips="$t('查看任务详情')">
                      {{ row.job_result.current_step || $t('正在运行') }}
                    </span>
                  </bk-button>
                </template>
              </auth-component>
              <div v-else>
                <auth-component
                  :authorized="row.permissions && row.permissions.operate"
                  :apply-info="[{
                    action: 'proxy_operate',
                    instance_id: row.bk_biz_id,
                    instance_name: row.bk_biz_name
                  }]">
                  <template #default="{ disabled }">
                    <bk-popover
                      placement="bottom"
                      :delay="400"
                      :width="language === 'zh-cn' ? 160 : 370"
                      :disabled="!row.re_certification || disabled"
                      :content="$t('认证资料过期不可操作', { type: $t('重装') })">
                      <bk-button
                        v-test="'reinstall'"
                        text
                        :disabled="row.re_certification || disabled"
                        @click="handleViewProxy(row, true, 'reinstall')"
                        ext-cls="row-btn">
                        {{ $t('重装') }}
                      </bk-button>
                    </bk-popover>
                    <bk-button
                      v-test="'edit'" text ext-cls="row-btn" :disabled="disabled" @click="handleViewProxy(row, true)">
                      {{ $t('编辑') }}
                    </bk-button>
                    <bk-popover
                      :ref="row['bk_host_id']"
                      theme="light agent-operate"
                      trigger="click"
                      :arrow="false"
                      offset="30, 5"
                      placement="bottom"
                      :disabled="disabled">
                      <bk-button v-test.common="'more'" :disabled="disabled" text ext-cls="row-btn">
                        {{ $t('更多') }}
                      </bk-button>
                      <template #content>
                        <ul class="dropdown-list">
                          <li
                            v-for="item in operate"
                            :key="item.id"
                            :class="['list-item', fontSize , { 'disabled': getDisabledStatus(item.id, row) }] "
                            v-test.common="`moreItem.${item.id}`"
                            v-show="getOperateShow(row, item)"
                            v-bk-tooltips="{
                              width: language === 'zh-cn' ? 160 : 370,
                              disabled: (item.id !== 'uninstall' && item.id !== 'reload') || !row.re_certification,
                              content: $t('认证资料过期不可操作', { type: $t('卸载') })
                            }"
                            @click="handleTriggerClick(item.id, row)">
                            {{ item.name }}
                          </li>
                        </ul>
                      </template>
                    </bk-popover>
                  </template>
                </auth-component>
              </div>
            </div>
          </template>
        </bk-table-column>

        <!--自定义字段显示列-->
        <bk-table-column
          key="setting"
          prop="colspanSetting"
          :render-header="renderHeader"
          width="42"
          :resizable="false"
          fixed="right">
        </bk-table-column>
      </bk-table>
    </div>

    <!--侧栏详情-->
    <CloudDetailSlider
      v-model="showSlider"
      :edit="isEdit"
      :row="currentRow"
      :edit-type="editType"
      @save="handleReloadTable">
    </CloudDetailSlider>
  </section>
</template>

<script lang="ts">
import { Component, Prop, Vue, Emit } from 'vue-property-decorator';
import { CloudStore, MainStore } from '@/store';
import ColumnSetting from '@/components/common/column-setting.vue';
import CloudDetailSlider from './cloud-detail-slider.vue';
import { STORAGE_KEY_COL } from '@/config/storage-key';
import { CreateElement } from 'vue/types/umd';
import { IProxyDetail } from '@/types/cloud/cloud';
import { IBkColumn, ITabelFliter } from '@/types';
import { TranslateResult } from 'vue-i18n';
import { DHCP_FILTER_KEYS } from '@/config/config';
import CopyDropdown, { allChildList } from '@/components/common/copy-dropdown.vue';

@Component({
  name: 'CloudDetailTable',
  components: {
    CloudDetailSlider,
    CopyDropdown,
  },
})

export default class CloudDetailTable extends Vue {
  @Prop({ type: Boolean, default: false }) private readonly loading!: boolean;
  @Prop({ type: Number, default: -1 }) private readonly id!: number;
  @Prop({ type: String, default: '' }) private readonly bkCloudName!: string;
  @Prop({ type: Array, default: () => [] }) private readonly proxyData!: IProxyDetail[];

  // slider
  private showSlider = false;
  private isEdit = false;
  private currentRow: Dictionary = {};
  // 打开编辑页面的操作类型
  private editType = '';
  // Proxy操作
  private operate = [
    { id: 'uninstall', name: this.$t('卸载'), disabled: false, show: true },
    // { id: 'remove', name: this.$t('移除'), disabled: false, show: true },
    { id: 'reboot', name: this.$t('重启'), disabled: false, show: true },
    { id: 'reload', name: this.$t('重载配置'), disabled: false, show: true },
    { id: 'upgrade', name: this.$t('升级'), disabled: false, show: true },
    { id: 'log', name: this.$t('最新执行日志'), disabled: false, show: true },
  ];
  // 状态map
  private statusMap = {
    running: this.$t('正常'),
    terminated: this.$t('异常'),
    not_installed: this.$t('未安装'),
    unknown: this.$t('未知'),
  };
  // Proxy列表加载
  private loadingProxy = false;
  // 列表字段显示配置
  private filter: { [key: string]: ITabelFliter } =  {};
  // value [checked, disabled, mockChecked, id, name]
  private filterSet: Dictionary[] = [
    { key: 'inner_ip', value: [true, true, true, 'inner_ip', this.$t('内网IPv4')] },
    { key: 'inner_ipv6', value: [true, true, true, 'inner_ipv6', this.$t('内网IPv6')] },
    { key: 'proxy_version', value: [true, false, true, 'version', this.$t('Proxy版本')] },
    { key: 'outer_ip', value: [false, false, false, 'outer_ip', this.$t('出口IP')] },
    { key: 'login_ip', value: [true, false, true, 'login_ip', this.$t('登录IP')] },
    { key: 'pagent_count', value: [true, false, true, 'pagent_count', this.$t('Agent数量')] },
    { key: 'bk_biz_name', value: [true, false, true, 'bk_biz_name', this.$t('归属业务')] },
    { key: 'is_manual', value: [false, false, false, 'is_manual', this.$t('安装方式')] },
    { key: 'proxy_status', value: [true, false, true, 'proxy_status', this.$t('Proxy状态')] },
    { key: 'created_at', value: [false, false, false, 'created_at', this.$t('安装时间')] },
    { key: 're_certification', value: [true, false, true, 're_certification', this.$t('密码/密钥')] },
    { key: 'bt', value: [false, false, false, 'peer_exchange_switch_for_agent', this.$t('BT节点探测')] },
    { key: 'speedLimit', value: [false, false, false, 'bt_speed_limit', this.$t('传输限速')] },
    { key: 'enable_compression', value: [false, false, false, 'enable_compression', this.$t('数据压缩')] },
  ];
  private localMark = '_proxy';
  private columnMinWidth: Dictionary = {};

  private get fontSize() {
    return MainStore.fontSize;
  }
  private get language() {
    return MainStore.language;
  }
  private get cloudList() {
    return CloudStore.cloudList;
  }
  private get authority() {
    return CloudStore.authority;
  }
  private get proxyOperateList() {
    return (this.authority.proxy_operate || []).map(item => item.bk_biz_id);
  }
  protected get copyMenu() {
    return allChildList.map(item => ({
      ...item,
      disabled: item.id.includes('v6')
        ? !this.proxyData.some(proxy => proxy.inner_ipv6)
        : !this.proxyData.some(proxy => proxy.inner_ip),
    }));
  }
  private get innerIPv6Width() {
    return this.proxyData.some(row => !!row.inner_ipv6) ? 270 : 100;
  }

  private created() {
    this.initCustomColStatus();
    this.computedColumnWidth();
  }
  // ...mapActions('cloud', ['setupProxy', 'operateJob', 'removeHost']),

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

  // 设置表格展示column的配置 filter
  public initCustomColStatus() {
    const columnsFilter = {};
    const list = this.$DHCP
      ? this.filterSet
      : this.filterSet.filter(item => !DHCP_FILTER_KEYS.includes(item.key));
    list.reduce((obj, item) => {
      const { key, value: [checked, disabled, mockChecked, id, name] } = item;
      obj[key] = { checked, disabled, mockChecked, id, name };
      return obj;
    }, columnsFilter);
    Object.assign(this.filter, columnsFilter);

    const data = this.handleGetStorage();
    if (data && Object.keys(data).length) {
      Object.keys(this.filter).forEach((key) => {
        this.filter[key].mockChecked = this.filter[key].disabled || !!data[key];
        this.filter[key].checked = this.filter[key].disabled || !!data[key];
      });
    }
  }
  // 更多操作事件
  public async handleTriggerClick(id: string, row: IProxyDetail) {
    const disabled = this.getDisabledStatus(id, row);
    if (disabled) return;
    (this.$refs[row.bk_host_id] as any)?.instance?.hide?.();
    switch (id) {
      case 'uninstall':
        this.handleConfirmOperate(this.$t('确定卸载该主机'), row, 'UNINSTALL_PROXY');
        break;
      case 'remove':
        this.handleConfirmOperate(this.$t('确定移除选择的主机'), row, this.handleRemoveHost);
        break;
      case 'reboot':
        this.handleConfirmOperate(this.$t('确定重启选择的主机'), row, 'RESTART_PROXY');
        break;
      case 'reload':
        // this.handleConfirmOperate(this.$t('确认重载所选主机的配置'), row, this.handleReload);
        // 重载改为在侧边栏编辑页面操作
        this.handleViewProxy(row, true, 'reload');
        break;
      case 'upgrade':
        this.handleConfirmOperate(this.$t('确定升级选择的主机'), row, 'UPGRADE_PROXY');
        break;
      case 'log':
        this.handleRouterPush('taskLog', { instanceId: row.job_result.instance_id, taskId: row.job_result.job_id });
    }
  }
  public handleConfirmOperate(title: string | TranslateResult, row: IProxyDetail, type: Function | string) {
    this.$bkInfo({
      title,
      extCls: 'wrap-title',
      confirmFn: () => {
        if (typeof type === 'function') {
          type(row);
        } else {
          this.handleOperateHost(row, type);
        }
      },
    });
  }
  /**
     * 升级主机、卸载主机、重启主机
     */
  public async handleOperateHost(row: IProxyDetail, type: string) {
    this.loadingProxy = true;
    const result = await CloudStore.operateJob({
      job_type: type,
      bk_host_id: [row.bk_host_id],
    });
    this.loadingProxy = false;
    if (result.job_id) {
      this.handleRouterPush('taskDetail', { taskId: result.job_id });
    }
  }
  /**
     * 移除主机
     */
  public async handleRemoveHost(row: IProxyDetail) {
    this.loadingProxy = true;
    const data = await CloudStore.removeHost({
      is_proxy: true,
      bk_host_id: [row.bk_host_id],
    });
    this.loadingProxy = false;
    if (data) {
      this.handleReloadTable();
    }
  }
  /**
     * 重装主机
     */
  public async handleReinstall(row: IProxyDetail) {
    this.loadingProxy = true;
    const result = await CloudStore.operateJob({
      job_type: 'REINSTALL_PROXY',
      bk_host_id: [row.bk_host_id],
    });
    this.loadingProxy = false;
    if (result.job_id) {
      this.handleRouterPush('taskDetail', { taskId: result.job_id });
    }
  }
  /**
     * 重载配置
     */
  public async handleReload(row: Dictionary) {
    this.loadingProxy = true;
    let paramKey = [
      'ap_id', 'bk_biz_id', 'bk_cloud_id', 'inner_ip', 'inner_ipv6',
      'is_manual', 'peer_exchange_switch_for_agent', 'bk_host_id', 'enable_compression','version'
    ];
    if (!this.$DHCP) {
      paramKey = paramKey.filter(key => !DHCP_FILTER_KEYS.includes(key));
    }
    const ipKeys = ['outer_ip']; // 没做区分展示的ip
    const paramExtraKey = ['bt_speed_limit', 'login_ip', 'data_ip'];
    const copyRow = Object.keys(row).reduce((obj: Dictionary, item) => {
      if (paramKey.includes(item)) {
        obj[item] = item === 'peer_exchange_switch_for_agent' ? row[item] + 0 : row[item];
      }
      if (paramExtraKey.includes(item) && row[item]) {
        obj[item] = row[item];
      }
      return obj;
    }, { os_type: 'LINUX' });
    ipKeys.forEach((key) => {
      if (this.$DHCP) {
        Object.assign(copyRow, this.$setIpProp(key, row));
      } else {
        copyRow[key] = row[key];
      }
    });
    const res = await CloudStore.setupProxy({ params: { job_type: 'RELOAD_PROXY', hosts: [copyRow] } });
    this.loadingProxy = false;
    // eslint-disable-next-line @typescript-eslint/prefer-optional-chain
    if (res && res.job_id) {
      this.handleRouterPush('taskDetail', { taskId: res.job_id });
    }
  }
  /**
     * 获取下线操作的禁用状态
     */
  public getDisabledStatus(id: string, row: IProxyDetail) {
    const ids = ['uninstall', 'remove'];
    const isExpired = id === 'uninstall' && row.re_certification;
    const exitNormalHost = this.proxyData.filter((item) => {
      const status = item.status?.toLowerCase();
      return item.bk_host_id !== row.bk_host_id && status === 'normal';
    }).length;
    return isExpired || (row.pagent_count !== 0 && ids.includes(id) && !exitNormalHost);
  }
  // 跳转日志详情
  public handleGotoLog(row: IProxyDetail) {
    if (!row || !row.job_result) return;
    this.handleRouterPush('taskLog', { instanceId: row.job_result.instance_id, taskId: row.job_result.job_id });
  }
  public handleFilterAgent() {
    const cloud = this.cloudList.find(item => Number(this.id) === item.bkCloudId);
    if (!cloud) return;
    this.handleRouterPush('agentStatus', { cloud: { id: cloud.bkCloudId, name: cloud.bkCloudName } });
  }
  public handleRouterPush(name: string, params: Dictionary, type = 'push') {
    (this.$router as Dictionary)[type]({ name, params });
  }
  @Emit('reload-proxy')
  public handleReloadTable() {
    return true;
  }

  // 编辑或查看proxy详细信息
  public handleViewProxy(row: IProxyDetail, isEdit: boolean, type?: string) {
    this.isEdit = isEdit;
    this.editType = type;
    this.showSlider = true;
    this.currentRow = row;
  }
  // 当前操作项是否显示
  public getOperateShow(row: IProxyDetail, config: Dictionary) {
    if (config.id === 'log' && (!row.job_result || !row.job_result.job_id)) {
      return false;
    }
    return config.show;
  }
  // 自定义字段显示列
  public renderHeader(h: CreateElement) {
    return h(ColumnSetting, {
      props: {
        filterHead: true,
        localMark: this.localMark,
        value: this.filter,
      },
      on: {
        update: (data: Dictionary) => this.handleColumnUpdate(data),
      },
    });
  }
  // tips类型表头
  public renderTipHeader(h: CreateElement, { column }: { column: IBkColumn }) {
    const directive = {
      name: 'bkTooltips',
      theme: 'light',
      content: this.$t('出口IP提示'),
      width: 238,
      placement: 'top',
    };
    return h('span', {
      class: { 'text-underline': true },
      directives: [directive],
    }, column.label);
  }
  // 字段显示列确认事件
  public handleColumnUpdate(data: Dictionary) {
    this.filter = data;
    this.$forceUpdate();
  }
  // 获取存储信息
  public handleGetStorage(): Dictionary {
    let data = {};
    try {
      data = JSON.parse(window.localStorage.getItem(this.localMark + STORAGE_KEY_COL) || '');
    } catch (_) {
      data = {};
    }
    return data;
  }
  // 合并最后两列
  public colspanHandle({ column }: { column: IBkColumn }) {
    if (column.property === 'colspanOperate') {
      return [1, 2];
    } if (column.property === 'colspanSetting') {
      return [0, 0];
    }
  }
  // 复制proxyIP
  public handleCopyIp(type: string) {
    const ipKey = this.$DHCP && type.includes('v6') ? 'inner_ipv6' : 'inner_ip';
    return Promise.resolve(this.proxyData.filter(proxy => proxy[ipKey]).map(proxy => proxy[ipKey]));
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  .row-btn {
    padding: 0;
    margin-right: 10px;
    white-space: nowrap;
  }
  .content-btn {
    margin-bottom: 14px;
  }
  .col-operate {
    @mixin layout-flex row, center;
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
  .link-pointer {
    color: #3a84ff;
    cursor: pointer;
  }
</style>
