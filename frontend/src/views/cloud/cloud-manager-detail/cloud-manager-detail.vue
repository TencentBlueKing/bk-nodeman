<template>
  <article class="cloud-manager-detail">
    <!--详情左侧面板-->
    <section class="detail-left">
      <!--搜索云区域别名-->
      <div class="detail-left-search">
        <bk-input
          :placeholder="$t('搜索云区域名称')"
          right-icon="bk-icon icon-search"
          v-model="bkCloudName"
          @change="handleValueChange">
        </bk-input>
      </div>
      <!--列表-->
      <div class="detail-left-list" ref="leftList" v-bkloading="{ isLoading: loading }">
        <ul>
          <auth-component
            class="list-auth-wrapper"
            v-for="(item, index) in area.data"
            :key="index"
            tag="li"
            :title="item.bkCloudName"
            :authorized="item.view"
            :apply-info="[{
              action: 'cloud_view',
              instance_id: item.bkCloudId,
              instance_name: item.bkCloudName
            }]">
            <template slot-scope="{ disabled }">
              <div
                class="list-item"
                :class="{ 'is-selected': item.bkCloudId === area.active, 'auth-disabled': disabled }"
                @click="handleAreaChange(item)">
                <span v-bk-tooltips="{
                  content: $t('存在异常Proxy'),
                  placement: 'top',
                  delay: [200, 0]
                }" v-if="item.exception === 'abnormal'" class="col-status">
                  <span class="status-mark status-terminated"></span>
                </span>
                <span class="list-item-name">{{ item.bkCloudName }}</span>
                <span v-bk-tooltips="{
                  content: $t('未安装Proxy'),
                  placement: 'top',
                  delay: [200, 0]
                }" v-if="!item.proxyCount" class="list-item-text error-text">
                  !
                </span>
                <span v-bk-tooltips="{
                  content: $t('proxy数量提示'),
                  placement: 'top',
                  width: 220,
                  delay: [200, 0]
                }" v-if="item.proxyCount === 1" class="list-item-text warning-text">
                  !
                </span>
              </div>
            </template>
          </auth-component>
          <li class="list-item loading" v-show="isListLoading">
            <loading-icon></loading-icon>
            <span class="loading-name">{{ $t('加载中') }}</span>
          </li>
        </ul>
      </div>
    </section>
    <!--右侧表格-->
    <section class="detail-right">
      <!--自定义三级导航-->
      <div class="detail-right-title mb20">
        <i class="title-icon nodeman-icon nc-back-left" @click="handleRouteBack"></i>
        <span class="title-name">{{ navTitle }}</span>
      </div>
      <!--表格-->
      <div class="detail-right-content">
        <div class="fs0">
          <auth-component
            tag="div"
            :authorized="!!proxyOperateList.length"
            :apply-info="[{ action: 'proxy_operate' }]">
            <template slot-scope="{ disabled }">
              <bk-button
                theme="primary"
                class="nodeman-primary-btn"
                ext-cls="content-btn"
                :disabled="disabled"
                @click="handleInstallProxy">
                {{ $t('安装Proxy') }}
              </bk-button>
            </template>
          </auth-component>
          <bk-popover>
            <bk-button ext-cls="ml10 content-btn" :disabled="!proxyData.length" @click="handleCopyIp">
              {{ $t('复制IP') }}
            </bk-button>
            <template #content>
              {{ $t('复制ProxyIP') }}
            </template>
          </bk-popover>
        </div>
        <div v-bkloading="{ isLoading: loadingProxy }">
          <bk-table :class="`head-customize-table ${ fontSize }`" :data="proxyData" :span-method="colspanHandle">
            <bk-table-column label="Proxy IP" show-overflow-tooltip>
              <template #default="{ row }">
                <bk-button text @click="handleShowDetail(row)" class="row-btn">{{ row.inner_ip }}</bk-button>
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('数据传输IP')"
              v-if="filter['outer_ip'].mockChecked"
              :render-header="renderTipHeader">
              <template #default="{ row }">
                <span>{{ row.outer_ip | emptyDataFilter }}</span>
              </template>
            </bk-table-column>
            <bk-table-column
              key="login_ip"
              :label="$t('登录IP')"
              prop="login_ip"
              v-if="filter['login_ip'].mockChecked">
              <template #default="{ row }">
                {{ row.login_ip || emptyDataFilter }}
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('归属业务')"
              prop="bk_biz_name"
              v-if="filter['bk_biz_name'].mockChecked" show-overflow-tooltip>
              <template #default="{ row }">
                <span>{{ row.bk_biz_name | emptyDataFilter }}</span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('Proxy状态')" prop="status" v-if="filter['proxy_status'].mockChecked">
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
            </bk-table-column>
            <bk-table-column :label="$t('密码密钥')" prop="re_certification" v-if="filter['re_certification'].mockChecked">
              <template #default="{ row }">
                <span :class="['tag-switch', { 'tag-enable': !row.re_certification }]">
                  {{ row.re_certification ? $t('过期') : $t('有效') }}
                </span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('Proxy版本')" prop="version" v-if="filter['proxy_version'].mockChecked">
              <template #default="{ row }">
                <span>{{ row.version | emptyDataFilter }}</span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('Agent数量')" prop="pagent_count" v-if="filter['pagent_count'].mockChecked">
              <template #default="{ row }">
                <span
                  class="link-pointer"
                  v-if="row.pagent_count"
                  @click="handleFilterAgent">
                  {{ row.pagent_count }}
                </span>
                <span v-else>0</span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('安装方式')" prop="is_manual" v-if="filter['is_manual'].mockChecked">
              <template #default="{ row }">
                {{ row.is_manual ? $t('手动') : $t('远程') }}
              </template>
            </bk-table-column>
            <bk-table-column
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
            </bk-table-column>
            <bk-table-column
              key="speedLimit"
              prop="bt_speed_limit"
              width="130"
              align="right"
              :label="`${$t('传输限速')}(MB/s)`"
              v-if="filter['speedLimit'].mockChecked">
              <template #default="{ row }">
                {{ row.bt_speed_limit || '--' }}
              </template>
            </bk-table-column>
            <bk-table-column
              v-if="filter['speedLimit'].mockChecked"
              min-width="20"
              :resizable="false">
            </bk-table-column>
            <bk-table-column
              :label="$t('安装时间')"
              width="200"
              prop="created_at"
              :resizable="false"
              v-if="filter['created_at'].mockChecked">
              <template #default="{ row }">
                {{ formatTimeByTimezone(row.created_at) }}
              </template>
            </bk-table-column>
            <bk-table-column prop="colspaOpera" :label="$t('操作')" width="148" :resizable="false" fixed="right">
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
                          :width="language === 'zh' ? 160 : 370"
                          :disabled="!row.re_certification || disabled"
                          :content="$t('认证资料过期不可操作', { type: $t('重装') })">
                          <bk-button
                            theme="primary"
                            text
                            :disabled="row.re_certification || disabled"
                            @click="handleReinstall(row)"
                            ext-cls="row-btn">
                            {{ $t('重装') }}
                          </bk-button>
                        </bk-popover>
                        <bk-button
                          theme="primary"
                          text
                          ext-cls="row-btn"
                          :disabled="disabled"
                          @click="handleEdit(row)">
                          {{ $t('编辑') }}
                        </bk-button>
                        <bk-popover ref="popoverRefList"
                                    theme="light agent-operate"
                                    trigger="click"
                                    :arrow="false"
                                    offset="30, 5"
                                    placement="bottom"
                                    :disabled="disabled">
                          <bk-button
                            theme="primary"
                            :disabled="disabled"
                            text
                            ext-cls="row-btn">
                            {{ $t('更多') }}
                          </bk-button>
                          <template #content>
                            <ul class="dropdown-list">
                              <li
                                v-for="item in operate"
                                :key="item.id"
                                :class="['list-item', fontSize , { 'disabled': getDisabledStatus(item.id, row) }] "
                                v-show="getOperateShow(row, item)"
                                v-bk-tooltips="{
                                  width: language === 'zh' ? 160 : 370,
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
              prop="colspaSetting"
              :render-header="renderHeader"
              width="42"
              :resizable="false"
              fixed="right">
            </bk-table-column>
          </bk-table>
        </div>
      </div>
    </section>
    <!--侧栏详情-->
    <section>
      <bk-sideslider
        :is-show.sync="sideslider.show"
        :width="sideslider.width"
        transfer
        quick-close
        @hidden="handleSidesHidden">
        <template #header>{{ sideslider.title }}</template>
        <template #content>
          <sideslider-content-edit
            :basic="basicInfo"
            v-if="sideslider.isEdit"
            @close="handleClose"
            @change="handleSideDataChange">
          </sideslider-content-edit>
          <sideslider-content :basic="basicInfo" v-else></sideslider-content>
        </template>
      </bk-sideslider>
    </section>
  </article>
</template>
<script lang="ts">
import { Component, Prop, Watch, Ref, Mixins } from 'vue-property-decorator';
import { MainStore, CloudStore } from '@/store/index';
import { copyText, debounce, isEmpty } from '@/common/util';
import ColumnSetting from '@/components/common/column-setting.vue';
import SidesliderContent from '../components/sideslider-content.vue';
import SidesliderContentEdit from '../components/sideslider-content-edit.vue';
import pollMixin from '@/common/poll-mixin';
import routerBackMixin from '@/common/router-back-mixin';
import { STORAGE_KEY_COL } from '@/config/storage-key';
import { CreateElement } from 'vue/types/umd';
import { ICloud, IProxyDetail } from '@/types/cloud/cloud';
import { IBkColumn, ITabelFliter } from '@/types';

@Component({
  name: 'cloud-manager-detail',
  components: {
    SidesliderContent,
    SidesliderContentEdit,
  },
  filters: {
    emptyDataFilter(v: string) {
      return !isEmpty(v) ? v : '--';
    },
  },
})

export default class CloudManagerDetail extends Mixins(pollMixin, routerBackMixin) {
  @Prop({ type: [Number, String], default: 0 }) private readonly id!: string | number;
  @Prop({ type: Boolean, default: true }) private readonly isFirst!: boolean; // 是否是首次加载
  @Prop({ type: String, default: '' }) private readonly search!: string;
  @Ref('leftList') private readonly leftList!: any;
  @Ref('popoverRefList') private readonly popoverRefList!: any[];

  private bkCloudName = this.search; // 别名
  private handleValueChange: Function = function () {}; // 别名搜索防抖
  private proxyData: IProxyDetail[] = []; // proxy表格数据
  // 区域列表
  private area: {
    list: ICloud[]
    data: ICloud[]
    isAll: boolean
    lastOffset: number
    offset: number
    active: number
  } = {
    list: [],
    data: [],
    isAll: false, // 标志是否加载完毕数据
    lastOffset: -1,
    offset: 0, // 上一次滚动的位置
    active: Number(this.id), // 当前选中的云区域
  };
  private loading = false;
  // 左侧列表加载状态
  private isListLoading = false;
  // Proxy操作
  private operate = [
    {
      id: 'uninstall',
      name: this.$t('卸载'),
      disabled: false,
      show: true,
    },
    {
      id: 'remove',
      name: this.$t('移除'),
      disabled: false,
      show: true,
    },
    {
      id: 'reboot',
      name: this.$t('重启'),
      disabled: false,
      show: true,
    },
    {
      id: 'reload',
      name: this.$t('重载配置'),
      disabled: false,
      show: true,
    },
    {
      id: 'upgrade',
      name: this.$t('升级'),
      disabled: false,
      show: true,
    },
    {
      id: 'log',
      name: this.$t('最新执行日志'),
      disabled: false,
      show: true,
    },
  ];
  // 状态map
  private statusMap = {
    running: this.$t('正常'),
    terminated: this.$t('异常'),
    unknown: this.$t('未知'),
  };
  // 侧滑
  private sideslider: Dictionary = {
    show: false,
    title: '',
    isEdit: false,
    width: 780,
  };
  // Proxy列表加载
  private loadingProxy = false;
  private basicInfo = {};
  private firstLoad = this.isFirst;
  // 列表字段显示配置
  private filter: { [key: string]: ITabelFliter } = {
    inner_ip: {
      checked: true,
      disabled: true,
      mockChecked: true,
      name: 'Proxy IP',
      id: 'inner_ip',
    },
    proxy_version: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('Proxy版本'),
      id: 'version',
    },
    outer_ip: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('数据传输IP'),
      id: 'outer_ip',
    },
    login_ip: {
      checked: false,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('登录IP'),
      id: 'login_ip',
    },
    pagent_count: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('Agent数量'),
      id: 'pagent_count',
    },
    bk_biz_name: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('归属业务'),
      id: 'bk_biz_name',
    },
    is_manual: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('安装方式'),
      id: 'is_manual',
    },
    proxy_status: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('Proxy状态'),
      id: 'proxy_status',
    },
    // inner_ip bk_biz_name status re_certification version pagent_count
    created_at: {
      checked: false,
      disabled: false,
      mockChecked: false,
      name: window.i18n.t('安装时间'),
      id: 'created_at',
    },
    re_certification: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('密码密钥'),
      id: 're_certification',
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
  };
  private localMark = '_proxy';

  private get fontSize() {
    return MainStore.fontSize;
  }
  private get permissionSwitch() {
    return MainStore.permissionSwitch;
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
  // 导航title
  private get navTitle() {
    const cloudArea = this.area.list.find(item => item.bkCloudId === this.area.active);
    return cloudArea ? cloudArea.bkCloudName : this.$t('未选中云区域');
  }
  private get proxyOperateList() {
    return this.authority.proxy_operate || [];
  }

  @Watch('id')
  private handleIdChange(newValue: string, oldValue: string) {
    if (!isEmpty(newValue) && parseInt(newValue, 10) !== parseInt(oldValue, 10)) {
      this.area.active = parseInt(newValue, 10);
      this.handleInit();
    }
  }
  private created() {
    this.handleInit();
  }
  private mounted() {
    this.handleValueChange = debounce(300, this.handleSearch);
  }

  private async handleInit() {
    this.initCustomColStatus();
    this.handleGetCloudList();
    this.handleGetProxyList();
  }
  private initCustomColStatus() {
    const data = this.handleGetStorage();
    if (data && Object.keys(data).length) {
      Object.keys(this.filter).forEach((key) => {
        this.filter[key].mockChecked = !!data[key];
        this.filter[key].checked = !!data[key];
      });
    }
  }
  /**
   * 搜索云区域别名
   */
  private handleSearch() {
    this.area.data = this.bkCloudName.length === 0
      ? this.area.list
      : this.area.list.filter((item) => {
        const originName = item.bkCloudName.toLocaleLowerCase();
        const currentName = this.bkCloudName.toLocaleLowerCase();
        return originName.indexOf(currentName) > -1;
      });
  }
  /**
   * 获取云区域列表
   */
  private async handleGetCloudList() {
    this.loading = true;
    const params: Dictionary = {};
    let list = [];
    if (!this.firstLoad) {
      list = this.cloudList;
    } else {
      list = await CloudStore.getCloudList(params);
    }
    this.area.list = this.permissionSwitch ? list.filter((item: ICloud) => item.view) : list;
    this.area.data = this.area.list;
    if (this.firstLoad) {
      this.$nextTick(() => {
        this.scrollToView();
      });
    }
    this.firstLoad = false;
    this.loading = false;
    this.handleSearch();
  }
  /**
   * 获取云区域Proxy列表
   */
  private async handleGetProxyList(loading = true) {
    this.loadingProxy = loading;
    this.proxyData = await CloudStore.getCloudProxyList({ bk_cloud_id: this.area.active });
    this.runingQueue = [];
    const isRunning = this.proxyData.some(item => item.job_result && item.job_result.status === 'RUNNING');
    if (isRunning) {
      this.runingQueue.push(this.area.active);
    }
    this.loadingProxy = false;
  }
  /**
   * 处理轮询的数据
   */
  public async handlePollData() {
    await this.handleGetProxyList(false);
  }
  /**
   * 返回上一层路由
   */
  private handleRouteBack() {
    this.routerBack();
  }
  /**
   * 新增Proxy
   */
  private handleInstallProxy() {
    this.$router.push({
      name: 'setupCloudManager',
      params: {
        type: 'create',
        id: `${this.id}`,
      },
    });
  }
  /**
   * 重装
   * @param {Object} row 当前行
   */
  private async handleReinstall(row: IProxyDetail) {
    const reinstall = async (row: IProxyDetail) => {
      this.loadingProxy = true;
      const result = await CloudStore.operateJob({
        job_type: 'REINSTALL_PROXY',
        bk_host_id: [row.bk_host_id],
      });
      this.loadingProxy = false;
      if (result.job_id) {
        this.$router.push({ name: 'taskDetail', params: { taskId: result.job_id, routerBackName: 'taskList' } });
      }
    };
    this.$bkInfo({
      title: this.$t('确定重装选择的主机'),
      confirmFn: () => {
        reinstall(row);
      },
    });
  }
  private async handleReload(row: Dictionary) {
    this.loadingProxy = true;
    const paramKey = [
      'ap_id', 'bk_biz_id', 'bk_cloud_id', 'inner_ip', 'outer_ip',
      'is_manual', 'peer_exchange_switch_for_agent', 'bk_host_id',
    ];
    const paramExtraKey = ['bt_speed_limit', 'login_ip', 'data_ip'];
    const copyRow = Object.keys(row).reduce((obj: Dictionary, item) => {
      if (paramKey.includes(item)) {
        obj[item] = item === 'peer_exchange_switch_for_agent' ? Number(row[item]) + 0 : row[item];
      }
      if (paramExtraKey.includes(item) && row[item]) {
        obj[item] = row[item];
      }
      return obj;
    }, { os_type: 'LINUX' });
    const res = await CloudStore.setupProxy({ params: { job_type: 'RELOAD_PROXY', hosts: [copyRow] } });
    this.loadingProxy = false;
    // eslint-disable-next-line @typescript-eslint/prefer-optional-chain
    if (res && res.job_id) {
      this.$router.push({ name: 'taskDetail', params: { taskId: res.job_id, routerBackName: 'taskList' } });
    }
  }
  private handleAreaChange(item: ICloud) {
    if (this.area.active === item.bkCloudId) return;
    this.$router.replace({
      name: 'cloudManagerDetail',
      params: {
        id: item.bkCloudId,
        isFirst: false,
        search: this.bkCloudName,
      },
    });
  }
  /**
   * 显示Proxy详情
   * @param { Object } row 当前行
   */
  private handleShowDetail(row: IProxyDetail) {
    this.setSideslider({
      show: true,
      title: row.inner_ip,
      isEdit: false,
      width: 780,
    }, row);
  }
  /**
   * 编辑Proxy
   */
  private handleEdit(row: IProxyDetail) {
    this.setSideslider({
      show: true,
      title: this.$t('修改登录信息'),
      isEdit: true,
      width: 600,
    }, row);
  }
  private setSideslider(data: Dictionary, row: IProxyDetail) {
    this.sideslider = data;
    this.$set(this, 'basicInfo', row);
  }
  /**
   * 替换Proxy
   * @param {Object} row 当前行
   */
  private handleReplace(row: IProxyDetail) {
    this.$router.push({
      name: 'setupCloudManager',
      params: {
        id: row.bk_cloud_id,
        innerIp: row.inner_ip,
        replaceHostId: row.bk_host_id,
        type: 'replace',
      },
    });
  }
  /**
   * 更多操作事件
   * @param {String} id
   */
  private async handleTriggerClick(id: string, row: IProxyDetail) {
    const disabled = this.getDisabledStatus(id, row);
    if (disabled) return;
    this.popoverRefList && this.popoverRefList[row.bk_host_id] && this.popoverRefList[row.bk_host_id].instance.hide();
    switch (id) {
      case 'replace':
        this.handleReplace(row);
        break;
      case 'uninstall':
        this.$bkInfo({
          title: this.$t('确定卸载该主机'),
          confirmFn: () => {
            this.handleOperateHost(row, 'UNINSTALL_PROXY');
          },
        });
        break;
      case 'remove':
        this.$bkInfo({
          title: this.$t('确定移除选择的主机'),
          confirmFn: () => {
            this.handleRemoveHost(row);
          },
        });
        break;
      case 'reboot':
        this.$bkInfo({
          title: this.$t('确定重启选择的主机'),
          confirmFn: () => {
            this.handleOperateHost(row, 'RESTART_PROXY');
          },
        });
        break;
      case 'reload':
        this.$bkInfo({
          title: this.$t('确定重载选择的主机配置'),
          confirmFn: () => {
            this.handleReload(row);
          },
        });
        break;
      case 'upgrade':
        this.$bkInfo({
          title: this.$t('确定升级选择的主机'),
          confirmFn: () => {
            this.handleOperateHost(row, 'UPGRADE_PROXY');
          },
        });
        break;
      case 'log':
        this.$router.push({
          name: 'taskLog',
          params: {
            instanceId: row.job_result.instance_id,
            taskId: row.job_result.job_id,
          },
        });
    }
  }
  /**
   * 主机操作：升级主机、卸载主机、重启主机
   */
  private async handleOperateHost(row: IProxyDetail, type: string) {
    this.loadingProxy = true;
    const result = await CloudStore.operateJob({
      job_type: type,
      bk_host_id: [row.bk_host_id],
    });
    this.loadingProxy = false;
    if (result.job_id) {
      this.$router.push({ name: 'taskDetail', params: { taskId: result.job_id, routerBackName: 'taskList' } });
    }
  }
  /**
   * 移除主机
   */
  private async handleRemoveHost(row: IProxyDetail) {
    this.loadingProxy = true;
    const data = await CloudStore.removeHost({
      is_proxy: true,
      bk_host_id: [row.bk_host_id],
    });
    this.loadingProxy = false;
    if (data) {
      this.handleGetProxyList();
    }
  }
  /**
   * 获取下线操作的禁用状态
   */
  private getDisabledStatus(id: string, row: IProxyDetail) {
    const ids = ['uninstall', 'remove'];
    const isExpired = id === 'uninstall' && row.re_certification;
    const exitNormalHost = this.proxyData.filter((item) => {
      const status = item.status?.toLowerCase();
      return item.bk_host_id !== row.bk_host_id && status === 'normal';
    }).length;
    return isExpired || (row.pagent_count !== 0 && ids.includes(id) && !exitNormalHost);
  }
  /**
   * 详情数据变更
   */
  private handleSideDataChange(data: IProxyDetail) {
    const index = this.proxyData.findIndex(item => item.bk_host_id === data.bk_host_id);
    if (index > -1) {
      this.handleGetProxyList(true);
      // this.$set(this.proxyData, index, Object.assign(this.proxyData[index], data))
    }
  }
  private handleSidesHidden() {
    this.$set(this, 'basicInfo', {});
  }
  /**
   * 跳转日志详情
   * @param {Object} row 当前行
   */
  private handleGotoLog(row: IProxyDetail) {
    if (!row || !row.job_result) return;
    this.$router.push({
      name: 'taskLog',
      params: {
        instanceId: row.job_result.instance_id,
        taskId: row.job_result.job_id,
      },
    });
  }
  /**
   * 当前操作项是否显示
   */
  private getOperateShow(row: IProxyDetail, config: Dictionary) {
    if (config.id === 'log' && (!row.job_result || !row.job_result.job_id)) {
      return false;
    }
    return config.show;
  }
  /**
   * 滚动列表到可视区域
   */
  private scrollToView() {
    if (!this.leftList) return;
    const itemHeight = 42; // 每项的高度
    const offsetHeight = itemHeight * this.area.list.findIndex(item => item.bkCloudId === this.area.active);
    if (offsetHeight > this.leftList.clientHeight) {
      this.leftList.scrollTo(0, offsetHeight - itemHeight);
    }
  }
  private handleClose() {
    this.sideslider.show = false;
  }
  /**
   * 自定义字段显示列
   * @param {createElement 函数} h 渲染函数
   */
  private renderHeader(h: CreateElement) {
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
  /**
   * tips类型表头
   */
  private renderTipHeader(h: CreateElement, { column }: { column: IBkColumn }) {
    const directive = {
      name: 'bkTooltips',
      theme: 'light',
      content: this.$t('数据传输IP提示'),
      width: 238,
      placement: 'top',
    };
    return h('span', {
      class: { 'text-underline': true },
      directives: [directive],
    }, column.label);
  }
  /**
   * 字段显示列确认事件
   */
  private handleColumnUpdate(data: Dictionary) {
    this.filter = data;
    this.$forceUpdate();
  }
  /**
   * 获取存储信息
   */
  private handleGetStorage(): Dictionary {
    let data = {};
    try {
      data = JSON.parse(window.localStorage.getItem(this.localMark + STORAGE_KEY_COL) || '');
    } catch (_) {
      data = {};
    }
    return data;
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
  private handleFilterAgent() {
    const cloud = this.cloudList.find(item => Number(this.id) === item.bkCloudId);
    if (!cloud) return;
    this.$router.push({
      name: 'agentStatus',
      params: {
        cloud: {
          id: cloud.bkCloudId,
          name: cloud.bkCloudName,
        },
      },
    });
  }
  private handleCopyIp() {
    const checkedIpText = this.proxyData.map(item => item.inner_ip).join('\n');
    if (!checkedIpText) return;
    const result = copyText(checkedIpText);
    if (result) {
      this.$bkMessage({ theme: 'success', message: this.$t('IP复制成功', { num: this.proxyData.length }) });
    }
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

.cloud-manager-detail {
  height: calc(100vh - 52px);

  @mixin layout-flex row;
  .detail-left {
    padding-top: 20px;
    flex: 0 0 240px;
    background-color: #fafbfd;
    &-search {
      margin-bottom: 16px;
      padding: 0 20px;
    }
    &-list {
      width: 240px;
      height: calc(100% - 55px);
      overflow-y: auto;
      .list-auth-wrapper {
        display: block;
      }
      .list-item {
        position: relative;
        display: flex;
        justify-content: space-between;
        padding-left: 40px;
        padding-right: 20px;
        line-height: 42px;
        height: 42px;
        font-size: 14px;
        cursor: pointer;
        &-name {
          flex: 1;
          max-width: 160px;
          display: inline-block;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
        }
        &-text {
          width: 13px;
          font-size: 14px;
          line-height: 42px;
          text-align: center;
          font-weight: 600;
        }
        .col-status {
          position: absolute;
          top: 14px;
          left: 20px;
        }
        .status-mark {
          margin-right: 0;
        }
        .error-text {
          color: #ea3636;
        }
        .warning-text {
          color: #ff9c01;
        }
        &:hover {
          background: #f0f1f5;
        }
        &.loading {
          color: #979ba5;
          .loading-name {
            font-size: 12px;
          }
        }
        &.is-selected {
          background: #e1ecff;
        }
        &.auth-disabled {
          color: #dcdee5;
          .list-item-text {
            color: #dcdee5;
          }
        }
      }
    }
  }
  .detail-right {
    flex: 1;
    padding: 20px 24px 0 24px;
    border-left: 1px solid #dcdee5;
    width: calc(100% - 240px);
    overflow-y: auto;
    &-title {
      line-height: 20px;

      @mixin layout-flex row;
      .title-icon {
        position: relative;
        top: -4px;
        height: 20px;
        font-size: 28px;
        color: #3a84ff;
        cursor: pointer;
      }
      .title-name {
        font-size: 16px;
        color: #313238;
      }
    }
    &-content {
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
    }
  }
}
</style>
