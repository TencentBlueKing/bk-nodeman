<template>
  <section class="sideslider-content">
    <bk-form form-type="vertical" :model="proxyData" ref="form" v-test="'proxyForm'">
      <bk-form-item :label="$t('内网IP')" required>
        <bk-input v-model="proxyData.inner_ip" readonly></bk-input>
      </bk-form-item>
      <bk-form-item
        :label="$t('数据传输IP')"
        property="outer_ip"
        error-display-type="normal"
        :rules="rules.outerIp"
        required
        :desc="descOuterIpTip">
        <bk-input v-model="proxyData.outer_ip"></bk-input>
      </bk-form-item>
      <bk-form-item :label="$t('登录IP')" property="login_ip" error-display-type="normal" :rules="rules.loginIp">
        <bk-input v-model="proxyData.login_ip" :placeholder="$t('留空默认为内网IP')"></bk-input>
      </bk-form-item>
      <bk-form-item :label="$t('认证方式')">
        <div class="item-auth">
          <bk-select v-model="proxyData.auth_type" :clearable="false" ext-cls="auth-select">
            <bk-option v-for="item in authentication"
                       :key="item.id"
                       :id="item.id"
                       :name="item.name">
            </bk-option>
          </bk-select>
          <div class="item-auth-content ml10" :class="{ 'is-error': showErrMsg }">
            <bk-input ext-cls="auth-input"
                      v-model="proxyData.password"
                      :type="passwordType"
                      :placeholder="$t('请输入')"
                      v-if="proxyData.auth_type === 'PASSWORD'"
                      @focus="handleFocus"
                      @blur="handleBlur">
            </bk-input>
            <bk-input ext-cls="auth-input"
                      :value="$t('自动拉取')"
                      v-else-if="proxyData.auth_type === 'TJJ_PASSWORD'"
                      readonly>
            </bk-input>
            <upload v-model="proxyData.key"
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
        <bk-input v-model="proxyData.data_path"></bk-input>
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
  </section>
</template>
<script lang="ts">
import { Vue, Component, Prop, Watch, Ref, Emit } from 'vue-property-decorator';
import { CloudStore } from '@/store';
import { isEmpty } from '@/common/util';
import { authentication } from '@/config/config';
import Upload from '@/components/setup-table/upload.vue';
import { IProxyDetail } from '@/types/cloud/cloud';
import { reguFnMinInteger, reguPort, reguIp, reguRequired, reguFnSysPath } from '@/common/form-check';

@Component({
  name: 'sideslider-content-edit',
  components: {
    Upload,
  },
})

export default class SidesliderContentEdit extends Vue {
  @Prop({ type: Object, default: () => ({}) }) private readonly basic!: IProxyDetail;
  @Ref('form') private readonly formRef!: any;

  private authentication = authentication;
  private descOuterIpTip = {
    width: 200,
    theme: 'light',
    content: this.$t('数据传输IP提示'),
  };
  private descDataPathTip = {
    width: 200,
    theme: 'light',
    content: this.$t('供proxy文件分发临时使用后台定期进行清理建议预留至少磁盘空间'),
  };
  private proxyData: Dictionary = {};
  private rules = {
    outerIp: [reguRequired, reguIp],
    loginIp: [
      {
        message: this.$t('IP不符合规范'),
        trigger: 'blur',
        validator: (val: string) => {
          if (isEmpty(val)) return true;
          const regx = '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$';
          return new RegExp(regx).test(val);
        },
      },
    ],
    port: [reguRequired, reguPort],
    account: [reguRequired],
    speedLimit: [reguFnMinInteger(1)],
    path: [reguRequired, reguFnSysPath()],
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
  public handlebasicChange(data: IProxyDetail) {
    this.proxyData = JSON.parse(JSON.stringify(data));
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
        outer_ip: this.proxyData.outer_ip,
        port: this.proxyData.port,
        data_path: this.proxyData.data_path,
      };
      if (this.proxyData.login_ip) {
        params.login_ip = this.proxyData.login_ip;
      }

      if (this.proxyData.auth_type) {
        const authType = this.proxyData.auth_type.toLocaleLowerCase();
        if (this.proxyData[authType]) {
          params.auth_type = this.proxyData.auth_type;
          params[authType] = this.proxyData[authType];
        }
      }
      if (this.proxyData.bt_speed_limit) {
        params.bt_speed_limit = this.proxyData.bt_speed_limit;
      }
      params.peer_exchange_switch_for_agent = Number(this.proxyData.peer_exchange_switch_for_agent || false);
      const result = await CloudStore.updateHost(params);
      if (result) {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('编辑成功如需加载最新配置请执行proxy重载'),
        });
        params.re_certification = false;
        this.handleChange(params);
        this.handleCancel();
      }
      this.loading = false;
    });
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
  private handleFileChange() {
    this.getAuthTypeValidate();
  }
  private getAuthTypeValidate() {
    this.showErrMsg = this.basic.re_certification
                  && isEmpty(this.proxyData[this.proxyData.auth_type.toLocaleLowerCase()]);
    return !this.showErrMsg;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

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
}
</style>
