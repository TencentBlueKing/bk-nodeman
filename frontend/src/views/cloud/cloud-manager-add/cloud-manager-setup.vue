<template>
  <section class="setup-cloud pb20" v-bkloading="{ isLoading: loading }">
    <div class="setup-cloud-left">
      <!--安装Proxy表单-->
      <section class="left-form">
        <!-- <tips :list="topTips" v-if="type === 'replace'" class="mb20"></tips> -->
        <tips class="mb20">
          <template #default>
            <ul>
              <template v-if="type === 'replace'">
                <li class="tips-content-item" v-for="(tip, index) in topTips" :key="index">
                  {{ tip }}
                </li>
              </template>
              <i18n path="Proxy安装要求tips" tag="li" class="tips-content-item">
                <bk-link class="tips-link" theme="primary" @click="handleToggle">{{ $t('安装要求') }}</bk-link>
              </i18n>
            </ul>
          </template>
        </tips>
        <bk-form :label-width="marginLeft" :model="formData" :rules="rules" ref="form">
          <install-method :is-manual="isManual" @change="installMethodHandle"></install-method>
          <bk-form-item :label="$t('安装信息')">
            <filter-ip-tips
              class="mb15 filter-tips"
              v-if="filterList.length && showFilterTips"
              @click="handleShowDetail">
            </filter-ip-tips>
            <!-- :local-mark="`proxy_setup`" -->
            <InstallTable
              v-if="!loading"
              ref="setupTable"
              :class="{ 'cloud-setup-table': isManual }"
              local-mark="proxy_setup`"
              :col-setting="false"
              :aps="apList"
              :bk-cloud-id="id"
              :arbitrary="apId"
              :setup-info="formData.bkCloudSetupInfo"
              :key="net.active"
              :before-delete="handleBeforeDeleteRow"
              @change="handleSetupTableChange"
              @choose="handleChoose">
            </InstallTable>
          </bk-form-item>
          <bk-form-item error-display-type="normal" :label="$t('密码/密钥')" required>
            <bk-radio-group v-model="formData.retention" class="content-basic">
              <bk-radio :value="1">{{ $t('保存1天') }}</bk-radio>
              <bk-radio class="ml35" :value="-1">{{ $t('长期保存') }}</bk-radio>
            </bk-radio-group>
          </bk-form-item>
          <bk-form-item error-display-type="normal" :label="$t('操作系统')" property="osType" required>
            <bk-select
              class="content-basic"
              :placeholder="$t('请选择')"
              v-model="formData.osType"
              :clearable="false"
              v-bk-tooltips.right="$t('仅支持Linux64位操作系统')"
              disabled>
              <bk-option id="LINUX" :name="$t('Linux64位')"></bk-option>
            </bk-select>
          </bk-form-item>
          <template v-if="!isManual">
            <bk-form-item error-display-type="normal" :label="$t('登录端口')" property="port" required>
              <bk-input class="content-basic" :placeholder="$t('请输入')" v-model="formData.port"></bk-input>
            </bk-form-item>
            <bk-form-item error-display-type="normal" :label="$t('登录账号')" property="account" required>
              <bk-input class="content-basic" :placeholder="$t('请选择')" v-model="formData.account"></bk-input>
            </bk-form-item>
          </template>
          <bk-form-item error-display-type="normal" :label="$t('归属业务')" property="bkBizId" required>
            <bk-biz-select
              v-model="formData.bkBizId"
              class="content-basic"
              :placeholder="$t('请选择业务')"
              :show-select-all="false"
              :multiple="false"
              :auto-update-storage="false">
            </bk-biz-select>
          </bk-form-item>
        </bk-form>
      </section>
      <!--操作按钮-->
      <section class="left-footer">
        <bk-button
          theme="primary"
          ext-cls="nodeman-primary-btn"
          :style="{ marginLeft: `${marginLeft}px` }"
          :loading="loadingSetup"
          @click="handleSetup">
          {{ saveBtnText }}
        </bk-button>
        <bk-button class="nodeman-cancel-btn ml5" @click="handleCancel">{{ $t('取消') }}</bk-button>
      </section>
    </div>
    <!--右侧提示栏-->
    <div class="setup-cloud-right" :class="{ 'right-panel': showRightPanel }">
      <right-panel v-model="showRightPanel" host-type="Proxy" :host-list="hostList"></right-panel>
      <!-- <right-panel v-model="showRightPanel" :list="tipsList" :tips="tips"></right-panel> -->
    </div>
    <!--过滤ip信息-->
    <filter-dialog v-model="showFilterDialog" :list="filterList" :title="$t('忽略详情')"></filter-dialog>
    <!-- agent包版本 -->
    <ChoosePkgDialog
      v-model="versionsDialog.show"
      :type="versionsDialog.type"
      :title="versionsDialog.title"
      :version="versionsDialog.version"
      :os-type="versionsDialog.os_type"
      :cpu-arch="versionsDialog.cpu_arch"
      :project="versionsDialog.project"
      @confirm="versionConfirm"
      @cancel="versionCancel" />
  </section>
</template>
<script lang="ts">
import { Component, Prop, Ref, Mixins } from 'vue-property-decorator';
import { MainStore, CloudStore, AgentStore } from '@/store/index';
import InstallTable from '@/components/setup-table/install-table.vue';
import InstallMethod from '@/components/common/install-method.vue';
import RightPanel from '@/components/common/right-panel-tips.vue';
import Tips from '@/components/common/tips.vue';
import FilterIpTips from '@/components/common/filter-ip-tips.vue';
import FilterIpMixin from '@/components/common/filter-ip-mixin';
import formLabelMixin from '@/common/form-label-mixin';
import FilterDialog from '@/components/common/filter-dialog.vue';
// import getTemplate from '../config/tips-template'
import { setupInfo, parentHead, setupDiffConfigs } from '../config/netTableConfig';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { defaultPort, getDefaultConfig } from '@/config/config';
import { ISetupHead, ISetupRow, IProxyIpKeys, ISetupParent } from '@/types';
import { reguPort, reguRequired } from '@/common/form-check';
import { getManualConfig } from '@/common/util';
import ChoosePkgDialog from '../../agent/components/choose-pkg-dialog.vue';

@Component({
  name: 'cloud-manager-setup',
  components: {
    InstallTable,
    InstallMethod,
    RightPanel,
    Tips,
    FilterIpTips,
    FilterDialog,
    ChoosePkgDialog,
  },
})

export default class CloudManagerSetup extends Mixins(formLabelMixin, FilterIpMixin) {
  @Prop({ type: [Number, String], required: true }) private readonly id!: number | string;
  @Prop({ type: String, default: '' }) private readonly innerIp!: string;
  // 操作类型 创建、替换
  @Prop({
    type: String,
    default: 'create',
    validator: (v: string) => ['create', 'replace'].includes(v),
  }) private readonly type!: string;
  // type 为 replace 时的主机ID
  @Prop({ type: Number, default: 0 }) private readonly replaceHostId!: number;
  @Ref('setupTable') private readonly setupTable!: any;
  @Ref('form') private readonly formRef!: any;

  private loading = true;
  private isManual = false; // 安装方式 目前跟type冲突，待处理
  // 表单数据
  private formData: Dictionary = {};
  private net = {
    list: [
      { name: this.$t('简单网络'), id: 'simple' },
      { name: this.$t('复杂网络'), id: 'complex' },
    ],
    active: 'simple',
  };
  // 表单校验
  private rules = {
    osType: [reguRequired],
    port: [reguRequired, reguPort],
    account: [reguRequired],
    bkBizId: [reguRequired],
  };
  private setupConfig: { header: ISetupHead[], parentHead: ISetupParent[], data: ISetupRow[] } = {
    header: setupInfo,
    parentHead,
    data: [],
  };
  // 是否显示右侧提示栏
  private showRightPanel = false;
  // 内网IP
  private innerIps = '';
  // 右侧面板提示
  private tips = this.$t('安装要求提示');
  // 顶部提示
  private topTips = [this.$t('替换Proxy提示一'), this.$t('替换Proxy提示二')];
  // 安装proxy加载状态
  private loadingSetup = false;
  // 接入点
  private apId = 0;
  private marginLeft = 108;
  private cloudName = '';
  private gse_version = '';

  // agent版本弹框显示参数
  public versionsDialog = {
    show: false,
    type: 'by_system_arch',
    title: this.$t('选择 Agent 版本'),
    version: '',
    os_type: 'linux',
    cpu_arch: '',
    project: 'gse_proxy',
    row: null as any,
    instance: null as any,
  };
  /**
   * 获取agent默认版本数据
   * @param {ISetupRow[]} data - 设置行数据
   * @returns {Promise<ISetupRow[]>} - 包含默认版本的数据
   */
  private defaultVersion = '';
  private async getDefaultVersion() {
    const { default_version } = await AgentStore.apiGetPkgVersion({
      project: 'gse_proxy',
      os: 'linux',
      cpu_arch: ''
    });
    this.defaultVersion = default_version;
  };

  // 选择agent版本
  public handleChoose({ row, instance }: { row: ISetupRow; instance: any; }) {
    const { version = '' } = row;
    this.versionsDialog.show = true;
    this.versionsDialog.version = version;
    this.versionsDialog.row = row;
    this.$nextTick(() => {
      this.versionsDialog.instance = instance;
      instance.handleFocus?.();
    });
  }
  public versionConfirm(info: { version: string; }) {
    this.versionsDialog.row.version = info.version;
    this.versionCancel();
  }
  public versionCancel() {
    this.versionsDialog.instance?.handleBlur?.();
  }
  private get apList() {
    return CloudStore.apList;
  }
  private get apUrl() {
    return CloudStore.apUrl;
  }
  // 保存按钮文案
  private get saveBtnText() {
    const textMap: Dictionary = {
      create: this.$t('安装'),
      replace: this.$t('替换'),
    };
    return textMap[this.type];
  }
  private get hostList() {
    return this.setupConfig.data.map((item: ISetupRow) => ({
      bk_cloud_id: Number(this.id),
      bk_cloud_name: this.cloudName,
      ap_id: this.apId,
      inner_ip: item ? item.inner_ip : '',
      outer_ip: item ? item.outer_ip : '',
    }));
  }

  private created() {
    this.handleInit();
  }
  private mounted() {
    this.marginLeft = this.initLabelWidth(this.formRef) || 0;
  }

  private async handleInit() {
    // 获取默认版本
    await this.getDefaultVersion();
    this.loading = true;
    switch (this.type) {
      case 'create':
        MainStore.setNavTitle('nav_安装Proxy');
        break;
      case 'replace':
        MainStore.setNavTitle(window.i18n.t('nav_替换Proxy', { ip: this.innerIp || this.id }));
        break;
    }
    await this.getCloudBizList(); // 拿到apId之后才能进行下一步
    if (!this.apList.length) {
      await CloudStore.getApList();
    }
    this.initForm();
    this.initTableData();
    CloudStore.setApUrl({ id: this.apId });
    this.loading = false;
  }
  // 是否显示agent包版本
  private get AgentPkgShow(): Boolean {
    // agent包开关开启并且接入点是v2版本时候显示agent包版本
    return MainStore.ENABLE_AGENT_PACKAGE_UI && this.isApV2;
  }
  private initForm() {
    // agent包开关关闭或者不是接入点v2版本时候不显示agent包版本
    if (!this.AgentPkgShow) {
      this.setupConfig.header = this.setupConfig.header?.filter(item => item.prop !== 'version');
    }
    this.formData = {
      bkCloudSetupInfo: this.setupConfig,
      retention: -1,
      osType: 'LINUX',
      port: getDefaultConfig('LINUX', 'port', defaultPort),
      account: getDefaultConfig('LINUX', 'account', 'root'),
      bkBizId: '',
    };
  }
  // 判断当前接入点是v2版本
  private get isApV2(): Boolean {
    return this.apList.find(data => data.id === this.apId)?.gse_version === 'V2';
  }
  /**
   * 重试回填数据
   */
  private initTableData() {
    const defaultAp = this.apList.find(item => item.is_default);
    // 设置默认版本
    const version = this.AgentPkgShow ? this.defaultVersion : '';
    const table = [];
    const initRow = {
      inner_ip: '',
      login_ip: '',
      outer_ip: '',
      auth_type: '',
      prove: '',
      retention: -1,
      data_path: defaultAp?.file_cache_dirs || '',
      version,
    };
    // 默认给两行数据
    table.push({ ...initRow });
    table.push({ ...initRow });
    this.setupConfig.data = table as ISetupRow[];
  }
  /**
   * 获取归属业务
   */
  private async getCloudBizList() {
    if (!this.id) return;
    const data = await CloudStore.getCloudDetail(`${this.id}`);
    this.apId = data.apId;
    this.cloudName = data.bkCloudName;
  }
  /**
   * 安装
   */
  private handleSetup() {
    Promise.all([
      this.setupTable.validate(),
      this.formRef.validate(),
    ]).then((result) => {
      const validate = result.every(item => !!item);
      if (validate) {
        const data = this.getFormData();
        const type = this.type === 'create' ? 'INSTALL_PROXY' : 'REPLACE_PROXY';
        this.handleCreateOrReplace(data, type);
      }
    });
  }
  /**
   * 获取表单数据
   */
  private getFormData(): ISetupRow[] {
    // 无替换操作 - 故当为手动安装时，直接把-1的接入点改为默认接入点
    let { apId } = this;
    if (this.isManual && this.apId === -1) {
      const ap = this.apList.find(item => item.is_default);
      apId = ap ? ap.id : 0;
    }
    return this.setupTable.getData().map((item: ISetupRow) => {
      const data: Dictionary = {
        ...item,
        retention: this.formData.retention,
        port: this.formData.port,
        account: this.formData.account,
        os_type: this.formData.osType,
        bk_biz_id: this.formData.bkBizId,
        bk_cloud_id: this.id,
        ap_id: apId,
        is_manual: this.isManual,
      };
      if (!data.login_ip) {
        delete data.login_ip;
      }
      if (!data.bt_speed_limit) {
        delete data.bt_speed_limit;
      } else {
        data.bt_speed_limit = Number(data.bt_speed_limit);
      }
      data.peer_exchange_switch_for_agent += 0;
      const authType = item.auth_type?.toLowerCase() as 'key' | 'password';
      if (item[authType]) {
        data[authType] = this.$safety.encrypt(item[authType] as string);
      }
      return data;
    });
  }
  /**
   * 创建和替换Proxy
   */
  private async handleCreateOrReplace(data: ISetupRow[], type = 'INSTALL_PROXY') {
    this.loadingSetup = true;
    const ipKeys: IProxyIpKeys[] = ['inner_ip', 'outer_ip', 'login_ip'];
    const versionList: { bk_host_id: number; version: string; }[] = [];
    const hosts = data.map((item: ISetupRow) => {
      const { inner_ip, outer_ip, login_ip, ...other } = item;
      const host: ISetupRow = {
        ...other,
      };
      ipKeys.forEach((key) => {
        Object.assign(host, this.$setIpProp(key, item));
      });
      versionList.push({
        bk_host_id: item.bk_host_id as number,
        version: item.version || '',
      });
      return host;
    });
    const params: Dictionary = { job_type: type, hosts };
    // 显示agent包版本，传agent信息
    if (this.AgentPkgShow) {
      Object.assign(params, {
        agent_setup_info: {
          choice_version_type: 'by_host',
          version_map_list: versionList,
        },
      });
    }
    if (type === 'REPLACE_PROXY') {
      params.replace_host_id = this.replaceHostId;
    }
    const res = await CloudStore.setupProxy({
      params,
      config: {
        needRes: true,
        globalError: false,
      },
    });
    this.loadingSetup = false;
    if (!res) return;

    if (res.result || res.code === 3801018) {
      // 部分忽略
      // mixin: handleFilterIp 处理过滤IP信息
      this.handleFilterIp(res.data);
    } else {
      const message = res.message ? res.message : this.$t('请求出错');
      this.$bkMessage({
        message,
        delay: 3000,
        theme: 'error',
      });
    }
  }
  /**
   * 取消
   */
  private handleCancel() {
    this.$router.push({
      name: 'cloudManager',
    });
  }
  /**
   * 监听内部IP属性变化
   */
  private handleSetupTableChange({ config }: { row: ISetupRow, config: ISetupHead }) {
    if (config.prop === 'inner_ip') {
      const tableData = this.setupTable.getTableData();
      this.innerIps = tableData.map((item: ISetupRow) => item.inner_ip).join(', ');
    }
  }
  /**
   * 安装方式切换
   */
  private installMethodHandle(isManual = false) {
    this.isManual = isManual;
    if (this.isManual) {
      this.setupConfig.header = getManualConfig(setupInfo, setupDiffConfigs);
    } else {
      this.setupConfig.header = setupInfo;
    }
    if (!this.AgentPkgShow) {
      this.setupConfig.header = this.setupConfig.header?.filter(item => item.prop !== 'version');
    }
    this.setupTable.handleInit();
    this.setupTable.handleScroll();
  }
  private handleToggle() {
    this.showRightPanel = true;
    this.setupConfig.data = this.getFormData();
  }
  private handleShowSetting() {
    this.setupTable.handleToggleSetting(true);
  }
  private handleBeforeDeleteRow(id: number, data: ISetupRow[], deleteFn: Function) {
    if (data.length <= 2) {
      this.$bkInfo({
        width: 450,
        title: this.$t('确定删除'),
        subTitle: this.$t('proxy安装建议'),
        confirmFn: () => {
          deleteFn();
        },
      });
    } else {
      deleteFn();
    }
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.setup-cloud {
  @mixin layout-flex row;
  &-left {
    flex: 1;
    .left-form {
      /* .cloud-setup-table {
        max-width: 822px;
      } */
      .content-basic {
        width: 480px;
      }
      .net-btn {
        width: 210px;
      }
      .filter-tips {
        margin-top: 8px;
      }
    }
    .left-footer {
      margin-top: 30px;
    }
  }
}
</style>
