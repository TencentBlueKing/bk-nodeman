<template>
  <section class="sideslider-content">
    <bk-form form-type="vertical" :model="proxyData" ref="form" v-test="'proxyForm'">
      <bk-form-item :label="$t('内网IPv4')" required>
        <bk-input v-model="proxyData.inner_ip" readonly></bk-input>
      </bk-form-item>
      <bk-form-item v-if="$DHCP" :label="$t('内网IPv6')" required>
        <bk-input v-model="proxyData.inner_ipv6" readonly></bk-input>
      </bk-form-item>
      <bk-form-item
        :label="$t('出口IP')"
        property="outer_ip"
        error-display-type="normal"
        :rules="rules.outerIp"
        required
        :desc="descOuterIpTip">
        <bk-input v-model="proxyData.outer_ip"></bk-input>
      </bk-form-item>
      <bk-form-item required :label="$t('登录IP')" property="login_ip" error-display-type="normal" :rules="rules.loginIp">
        <bk-input v-model="proxyData.login_ip" :placeholder="$t('留空默认为内网IP')"></bk-input>
      </bk-form-item>
      <bk-form-item :label="$t('认证方式')">
        <div class="item-auth">
          <bk-select v-model="proxyData.auth_type" :clearable="false" ext-cls="auth-select">
            <bk-option
              v-for="item in authentication"
              :key="item.id"
              :id="item.id"
              :name="item.name">
            </bk-option>
          </bk-select>
          <div class="item-auth-content ml10" :class="{ 'is-error': showErrMsg }">
            <InstallInputType
              class="auth-input"
              v-model.trim="proxyData.password"
              type="password"
              :placeholder="$t('请输入')"
              v-if="proxyData.auth_type === 'PASSWORD'"
              :pwd-fill="!proxyData.re_certification"
              @focus="handleFocus"
              @blur="handleBlur" />
            <bk-input
              ext-cls="auth-input"
              :value="$t('自动拉取')"
              v-else-if="proxyData.auth_type === 'TJJ_PASSWORD'"
              readonly>
            </bk-input>
            <upload
              :value="proxyData.key"
              class="auth-key"
              parse-text
              :max-size="10"
              unit="KB"
              @change="handleFileChange"
              v-else>
            </upload>
            <p class="error-tip" v-if="showErrMsg">{{ $t('认证资料过期') }}</p>
          </div>
        </div>
      </bk-form-item>
      <bk-form-item :label="$t('登录端口')" property="port" error-display-type="normal" :rules="rules.port" required>
        <bk-input v-model="proxyData.port"></bk-input>
      </bk-form-item>
      <bk-form-item :label="$t('登录账号')" property="account" error-display-type="normal" :rules="rules.account" required>
        <bk-input v-model="proxyData.account"></bk-input>
      </bk-form-item>
      <bk-form-item
        :label="$t('临时文件目录')"
        property="data_path"
        error-display-type="normal"
        required
        :desc="descDataPathTip"
        :rules="rules.path">
        <bk-input v-model="proxyData.data_path" @blur="(value) => pathInputBlur(value, 'data_path')" />
      </bk-form-item>
      <bk-form-item :label="$t('BT节点探测')" property="peer_exchange_switch_for_agent">
        <bk-switcher
          theme="primary"
          size="small"
          v-model="proxyData.peer_exchange_switch_for_agent">
        </bk-switcher>
      </bk-form-item>
      <bk-form-item :label="$t('传输限速')" property="bt_speed_limit" error-display-type="normal" :rules="rules.speedLimit">
        <bk-input v-model="proxyData.bt_speed_limit"></bk-input>
      </bk-form-item>
      <bk-form-item v-if="$DHCP" :label="$t('数据压缩')" property="enable_compression">
        <bk-switcher
          theme="primary"
          size="small"
          v-model="proxyData.enable_compression">
        </bk-switcher>
      </bk-form-item>
      <bk-form-item
        v-show="AgentPkgShow"
        :required="AgentPkgShow"
        :rules="rules.version"
        error-display-type="normal"
        property="version"
        :label="$t('agent版本')">
        <div style="display: flex; flex-wrap: wrap; max-width: 600px;">
          <bk-form-item
            class="version-type"
            error-display-type="normal"
            property="agent_version">
            <div
              :class="['versions-choose-btn flex', { 'versions-choose-detail': proxyData.version }]"
              @click="() => chooseAgentVersion({ version: proxyData.version })">
              <template v-if="proxyData.version" class="versions-choose-detail">
                <div class="prefix-area">
                  <i class="nodeman-icon nc-package-2" />
                </div>
                <div class="version-text">{{ proxyData.version }}</div>
                <i class="nodeman-icon nc-icon-edit-2 versions-choose-icon" />
              </template>
              <template v-else>
                <i class="nodeman-icon nc-plus-line" />
                {{ $t('选择版本') }}
              </template>
            </div>
          </bk-form-item>
        </div>
      </bk-form-item>
    </bk-form>
    <div class="mt30 mb10">
      <bk-button
        v-test.common="'formCommit'"
        theme="primary"
        class="nodeman-cancel-btn"
        :loading="loading"
        @click="handleSave">
        {{ $t('保存') }}
      </bk-button>
      <bk-button class="nodeman-cancel-btn ml10" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </div>
    <!-- agent包版本 -->
    <ChoosePkgDialog
      v-model="versionsDialog.show"
      :type="versionsDialog.type"
      :title="versionsDialog.title"
      :version="versionsDialog.version"
      :os-type="versionsDialog.os_type"
      :project="versionsDialog.project"
      @confirm="updateAgentVersion" />
  </section>
</template>
<script lang="ts">
import { Vue, Component, Prop, Watch, Ref, Emit } from 'vue-property-decorator';
import { CloudStore, MainStore } from '@/store';
import { isEmpty } from '@/common/util';
import { authentication, DHCP_FILTER_KEYS } from '@/config/config';
import Upload from '@/components/setup-table/upload.vue';
import { IProxyDetail } from '@/types/cloud/cloud';
import InstallInputType from '@/components/setup-table/install-input-type.vue';
import { reguFnMinInteger, reguPort, reguIPMixins, reguRequired, reguFnSysPath, osDirReplace } from '@/common/form-check';
import ChoosePkgDialog from '../../agent/components/choose-pkg-dialog.vue';


@Component({
  name: 'sideslider-content-edit',
  components: {
    Upload,
    InstallInputType,
    ChoosePkgDialog,
  },
})

export default class SidesliderContentEdit extends Vue {
  @Prop({ type: Object, default: () => ({}) }) private readonly basic!: IProxyDetail;
  @Prop({ type: String, default: '' }) private readonly editType!: string;
  @Ref('form') private readonly formRef!: any;

  private authentication = authentication;
  private descOuterIpTip = {
    width: 200,
    theme: 'light',
    content: this.$t('出口IP提示'),
  };
  private descDataPathTip = {
    width: 200,
    theme: 'light',
    content: this.$t('供proxy文件分发临时使用后台定期进行清理建议预留至少磁盘空间'),
  };
  // agent包版本弹框参数
  public versionsDialog = {
    show: false,
    type: 'by_system_arch',
    title: this.$t('选择 Agent 版本'),
    version: '',
    os_type: 'linux',
    project: 'gse_proxy'
  };
  // 选择agent版本
  public chooseAgentVersion(info: {
    version: string;
  }) {
    const { version = '' } = info;
    this.versionsDialog.show = true;
    this.versionsDialog.version = version;
  }
  // 回填agent版本
  public updateAgentVersion(info: any) {
    this.proxyData.version = info.version;
  }
  // 获取接入点列表
  private get apList() {
    return CloudStore.apList;
  }
  // 判断当前agent是否打开且接入点是v2版本
  public get AgentPkgShow(): Boolean {
    return MainStore.ENABLE_AGENT_PACKAGE_UI && this.apList.find(data => data.id === this.proxyData.ap_id)?.gse_version === 'V2';
  }
  private proxyData: Dictionary = {};
  private get rules() {
    const commonRules = {
      outerIp: [reguRequired, reguIPMixins],
      loginIp: [reguRequired, reguIPMixins],
      port: [reguRequired, reguPort],
      account: [reguRequired],
      speedLimit: [reguFnMinInteger(1)],
      path: [reguRequired, reguFnSysPath({ minLevel: 2 })],
      version: this.AgentPkgShow ? [reguRequired] : [],
    };
    return commonRules;
  };
  private loading = false;
  private showErrMsg = false;

  private get passwordType(): string {
    if (!isEmpty(this.proxyData.password)) {
      return 'password';
    }
    return 'text';
  }

  @Watch('basic', { immediate: true })
  public async handlebasicChange(data: IProxyDetail) {
    this.proxyData = JSON.parse(JSON.stringify(data));
    if (!this.apList.length) {
      await CloudStore.getApList();
    }
  }
  @Watch('proxyData', { deep: true })
  public handleFormChange() {
    this.$emit('update-edited', true);
  }

  private handleSave() {
    const isValidate = this.getAuthTypeValidate();

    if (!isValidate) return;
    this.formRef.validate().then(async () => {
      this.loading = true;
      const params: Dictionary = {
        bk_cloud_id: this.proxyData.bk_cloud_id,
        bk_host_id: this.proxyData.bk_host_id,
        account: this.proxyData.account,
        port: this.proxyData.port,
        data_path: this.proxyData.data_path,
      };
      Object.assign(params, this.$setIpProp('outer_ip', this.proxyData));
      if (this.proxyData.login_ip) {
        Object.assign(params, this.$setIpProp('login_ip', this.proxyData));
      }
      if (this.$DHCP) {
        params.enable_compression = !!this.proxyData.enable_compression;
      }

      if (this.proxyData.auth_type) {
        const authType = this.proxyData.auth_type.toLocaleLowerCase();
        if (this.proxyData[authType]) {
          params.auth_type = this.proxyData.auth_type;
          params[authType] = this.$safety.encrypt(this.proxyData[authType]);
        }
      }
      if (this.proxyData.bt_speed_limit) {
        params.bt_speed_limit = this.proxyData.bt_speed_limit;
      }
      params.peer_exchange_switch_for_agent = Number(this.proxyData.peer_exchange_switch_for_agent || false);
      this.proxyData.version && (params.version = this.proxyData.version);
      const result = await CloudStore.updateHost(params);
      if (result) {
        if (this.editType === 'reinstall') {
          // 重装
          this.handleReinstall(this.basic);
        } else if (this.editType === 'reload') {
          // 重载
          const basicInfo = JSON.parse(JSON.stringify(this.basic));
          Object.assign(basicInfo, params);
          this.handleReload(basicInfo);
        } else {
          this.$bkMessage({
            theme: 'success',
            message: this.$t('编辑成功如需加载最新配置请执行proxy重载'),
          });
        }
        params.re_certification = false;
        this.handleChange(params);
        this.handleCancel();
      }
      this.loading = false;
    });
  }
  // 跳转到代理重装和重载页面
  public handleRouterPush(name: string, params: Dictionary, type = 'push') {
    (this.$router as Dictionary)[type]({ name, params });
  }
  /**
   * 重装主机
  */
  public async handleReinstall(row: IProxyDetail) {
    const result = await CloudStore.operateJob({
      job_type: 'REINSTALL_PROXY',
      bk_host_id: [row.bk_host_id],
    });
    if (result.job_id) {
      this.handleRouterPush('taskDetail', { taskId: result.job_id });
    }
  }
  /**
   * 重载配置
  */
  public async handleReload(row: Dictionary) {
    let paramKey = [
      'ap_id', 'bk_biz_id', 'bk_cloud_id', 'inner_ip', 'inner_ipv6',
      'is_manual', 'peer_exchange_switch_for_agent', 'bk_host_id', 'enable_compression', 'version'
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
    if (res?.job_id) {
      this.handleRouterPush('taskDetail', { taskId: res.job_id });
    }
  }
  @Emit('change')
  private handleChange(params: any) {
    return params;
  }
  @Emit('close')
  private handleCancel() {}
  private handleFocus() {
    this.showErrMsg = false;
  }
  private handleBlur() {
    this.getAuthTypeValidate();
  }
  private handleFileChange({ value = '' }) {
    this.proxyData.key = value;
    this.getAuthTypeValidate();
  }
  private getAuthTypeValidate() {
    this.showErrMsg = this.basic.re_certification
                  && isEmpty(this.proxyData[this.proxyData.auth_type.toLocaleLowerCase()]);
    return !this.showErrMsg;
  }
  public pathInputBlur(val: string, prop: string) {
    this.proxyData[prop] = `/${osDirReplace(val)}`;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";
@import "@/css/variable.css";

>>> .bk-form.bk-form-vertical .bk-form-item+.bk-form-item {
  margin-top: 12px;
}
.sideslider-content {
  padding: 24px 30px 0 30px;
  .item-auth {
    @mixin layout-flex row, center;
    &-content {
      flex: 1;
      &.is-error {
        >>> input[type=text] {
          border-color: #ff5656;
        }
        >>> button.upload-btn {
          border: 1px solid #ff5656;
        }
      }
    }
    .error-tip {
      position: absolute;
      margin: 4px 0 0;
      font-size: 12px;
      color: #ea3636;
      line-height: 1;
    }
    .auth-select {
      width: 124px;
    }
    .auth-input {
      flex: 1;
    }
    .auth-key {
      width: 100%;
    }
  }
  .version-type {
    width: 100%;
    >>> .bk-form-content {
      margin-left: 0!important;
    }
    &.is-error .versions-choose-btn:not(:hover) {
      border-color: #ff5656;
    }
  }
  .versions-choose-btn {
    width: 100%;
    position: relative;
    align-items: center;
    justify-content: center;
    border: 1px dashed #c4c6cc;
    border-radius: 2px;
    background-color: #fafbfd;
    cursor: pointer;
    .nc-plus-line {
      margin-right: 6px;
    }
    .nodeman-icon {
      color: #979ba5;
    }
    &:hover {
      color: $primaryFontColor;
      border-color: $primaryFontColor;
    }
    &:hover .nodeman-icon {
      color: $primaryFontColor;
    }
  }
  .versions-choose-detail {
    border-style: solid;
    .prefix-area {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 30px;
      border-right: 1px solid #c4c6cc;
      background-color: #fafbfd;
    }
    .version-text {
      padding: 0 8px;
      flex: 1;
      color: #63656e;
      background-color: #fff;
    }
    .versions-choose-icon {
      position: absolute;
      right: 8px;
      top: 8px;
      display: none;
    }
    &:hover {
      .prefix-area {
        background-color: #e1ecff;
        border-color: $primaryFontColor;
      }
      .versions-choose-icon {
        display: inline-block;
      }
    }
  }
}
</style>
