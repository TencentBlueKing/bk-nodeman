<template>
  <div class="access-point-host">
    <bk-form :label-width="labelWidth" :model="formData" ref="formData">
      <bk-form-item
        :label="$t('接入点名称')"
        :required="true" :rules="rules.name"
        property="name"
        error-display-type="normal">
        <bk-input v-model.trim="formData.name" :placeholder="$t('用户创建的接入点')" @change="hadleFormChange"></bk-input>
      </bk-form-item>
      <bk-form-item :label="$t('接入点说明')">
        <bk-input
          ext-cls="bg-white textarea-description"
          type="textarea"
          :rows="4"
          :maxlength="100"
          :placeholder="$t('接入点说明placeholder')"
          v-model.trim="formData.description"
          @change="hadleFormChange">
        </bk-input>
      </bk-form-item>
      <bk-form-item
        :label="$t('区域')"
        :required="true"
        :rules="rules.required"
        property="region_id"
        error-display-type="normal">
        <bk-input v-model.trim="formData.region_id" :placeholder="$t('请输入')" @change="hadleFormChange"></bk-input>
      </bk-form-item>
      <bk-form-item
        :label="$t('城市')"
        :required="true"
        :rules="rules.required"
        property="city_id"
        error-display-type="normal">
        <bk-input v-model.trim="formData.city_id" :placeholder="$t('请输入')" @change="hadleFormChange"></bk-input>
      </bk-form-item>
      <bk-form-item
        class="mt40"
        :label="$t('Zookeeper用户名')"
        :required="false"
        property="zk_account"
        error-display-type="normal">
        <bk-input v-model.trim="formData.zk_account" :placeholder="$t('请输入')" @change="hadleFormChange"></bk-input>
      </bk-form-item>
      <bk-form-item
        :label="$t('Zookeeper密码')"
        :required="false"
        property="zk_password"
        error-display-type="normal">
        <bk-input
          :type="zkPasswordType"
          v-model.trim="formData.zk_password"
          :placeholder="$t('请输入')"
          @change="hadleFormChange">
        </bk-input>
      </bk-form-item>
      <div
        v-for="(label, labelIndex) in labelTableList" :key="labelIndex"
        :style="{ width: `${relatedContentWidth}px` }"
        :class="['bk-form-item ip-related-item clearfix', { mb40: !labelIndex }]">
        <div class="bk-form-item is-required">
          <label class="bk-label" :style="{ width: `${ labelWidth }px` }">
            <span class="bk-label-text">{{label.name}}</span>
          </label>
          <div class="bk-form-content" :style="{ 'margin-left': `${ labelWidth }px` }">
            <setup-form-table
              ref="zookeeperTable"
              :table-head="checkConfig[label.thead]">
              <tbody class="setup-body" slot="tbody">
                <tr v-for="(host, index) in formData[label.key]" :key="`${label.key}td${index}`">
                  <td>{{ index + 1 }}</td>
                  <td
                    class="is-required"
                    v-for="(config, idx) in checkConfig[label.key]"
                    :key="`${label.key}td${idx}`">
                    <verify-input
                      position="right"
                      ref="checkItem"
                      required
                      :rules="config.rules"
                      :id="index"
                      :default-validator="getDefaultValidator()">
                      <input-type
                        v-model.trim="host[config.prop]"
                        v-bind="{
                          type: 'text',
                          placeholder: $t('请输入'),
                          disabled: checkLoading
                        }"
                        @change="hadleFormChange">
                      </input-type>
                    </verify-input>
                  </td>
                  <td>
                    <div class="opera-icon-group">
                      <i
                        :class="['nodeman-icon nc-plus', { 'disable-icon': checkLoading }]"
                        @click="addAddress(index, label.key)">
                      </i>
                      <i
                        :class="['nodeman-icon nc-minus', { 'disable-icon': formData[label.key].length <= 1 }]"
                        @click="deleteAddress(index, label.key)">
                      </i>
                    </div>
                  </td>
                </tr>
              </tbody>
            </setup-form-table>
          </div>
        </div>
      </div>
      <bk-form-item
        class="mt20"
        :label="$t('外网回调地址')"
        :rules="rules.callback"
        property="outer_callback_url"
        error-display-type="normal">
        <bk-input
          v-model.trim="formData.outer_callback_url"
          :disabled="checkLoading"
          :placeholder="$t('请输入外网回调地址')"
          @change="hadleFormChange">
        </bk-input>
      </bk-form-item>
      <bk-form-item
        class="mt40"
        :label="$t('Agent包服务器目录')"
        :required="false"
        :rules="rules.nginxPath"
        property="nginx_path"
        error-display-type="normal">
        <bk-input
          v-model.trim="formData.nginx_path"
          :disabled="checkLoading"
          :placeholder="$t('请输入服务器目录')"
          @change="hadleFormChange">
        </bk-input>
      </bk-form-item>
      <bk-form-item
        class="mt20"
        :label="$t('Agent包URL')"
        :required="true"
        :rules="rules.url"
        property="package_inner_url"
        error-display-type="normal">
        <bk-input
          v-model.trim="formData.package_inner_url"
          :disabled="checkLoading"
          :placeholder="$t('请输入内网下载URL')"
          @change="hadleFormChange">
        </bk-input>
      </bk-form-item>
      <bk-form-item class="mt10" label="" :rules="rules.url" property="package_outer_url" error-display-type="normal">
        <bk-input
          v-model.trim="formData.package_outer_url"
          :disabled="checkLoading"
          :placeholder="$t('请输入外网下载URL')"
          @change="hadleFormChange">
        </bk-input>
      </bk-form-item>
      <bk-form-item class="mt30">
        <bk-button
          class="check-btn"
          theme="primary"
          :loading="checkLoading"
          :disabled="checkedResult"
          @click.stop="checkCommit">
          {{ $t('测试Server及URL可用性') }}
        </bk-button>
        <section class="check-result" v-if="isChecked">
          <div class="check-result-detail">
            <template v-if="isChecked">
              <h4 class="result-title">{{ $t('测试结果') }}</h4>
              <template v-for="(info, index) in checkedResultList">
                <p :key="index" :class="{ error: info.log_level === 'ERROR' }">{{ `- ${ info.log }` }}</p>
              </template>
            </template>
          </div>
        </section>
      </bk-form-item>
      <bk-form-item class="item-button-group mt30">
        <bk-button
          class="nodeman-primary-btn"
          theme="primary"
          :disabled="!checkedResult || checkLoading"
          @click="submitInfo">
          {{ $t('下一步') }}
        </bk-button>
        <bk-button
          class="nodeman-cancel-btn"
          @click="cancel">
          {{ $t('取消') }}
        </bk-button>
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Ref, Watch } from 'vue-property-decorator';
import { MainStore, ConfigStore } from '@/store/index';
import { IApBase, IIpGroup, IZk } from '@/types/config/config';
import VerifyInput from '@/components/common/verify-input.vue';
import InputType from '@/components/setup-table/input-type.vue';
import formLabelMixin from '@/common/form-label-mixin';
import SetupFormTable from './step-form-table.vue';
import { isEmpty } from '@/common/util';

type IServer = 'btfileserver' | 'dataserver' | 'taskserver';

const ipRegExp = '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$';
@Component({
  name: 'StepHost',
  components: {
    VerifyInput,
    InputType,
    SetupFormTable,
  },
})
export default class StepHost extends formLabelMixin {
  @Prop({ type: [String, Number], default: '' }) private readonly pointId!: string | number;
  @Prop({ type: Boolean, default: false }) private readonly stepCheck!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly isEdit!: boolean;
  @Ref('formData') private readonly formDataRef!: any;
  @Ref('checkItem') private readonly checkItem!: any[];

  private checkLoading = false;
  private isInit = true;
  private checkedResult = false; // 检测结果
  private isChecked = false; // 是否已进行过检测
  private checkedResultList = []; // 检测详情
  private formData: IApBase = {
    name: '',
    description: '',
    region_id: '',
    city_id: '',
    zk_account: '',
    zk_password: '',
    zk_hosts: [
      {
        zk_ip: '',
        zk_port: '',
      },
    ],
    btfileserver: [
      { inner_ip: '', outer_ip: '' },
    ],
    dataserver: [
      { inner_ip: '', outer_ip: '' },
    ],
    taskserver: [
      { inner_ip: '', outer_ip: '' },
    ],
    outer_callback_url: '',
    package_inner_url: '',
    package_outer_url: '',
    nginx_path: '',
  };
  private labelTableList = [
    { name: 'Zookeeper', key: 'zk_hosts', thead: 'zkHead' },
    { name: 'Btfileserver', key: 'btfileserver', thead: 'head' },
    { name: 'Dataserver', key: 'dataserver', thead: 'head' },
    { name: 'Taskserver', key: 'taskserver', thead: 'head' },
  ];
  private checkConfig = {
    zkHead: [
      { name: this.$t('序号'), width: 60 },
      { name: 'IP', width: 230 },
      { name: 'PORT', width: 230 },
      { name: '', width: 70 },
    ],
    head: [
      { name: this.$t('序号'), width: 60 },
      { name: this.$t('内网IP'), width: 230 },
      { name: this.$t('外网IP'), width: 230 },
      { name: '', width: 70 },
    ],
    zk_hosts: [
      {
        prop: 'zk_ip',
        classExt: 'ip-input ip-input-inner',
        required: true,
        placeholder: window.i18n.t('请输入Zookeeper主机的IP'),
        rules: [
          {
            regx: ipRegExp,
            content: this.$t('IP格式不正确'),
          },
          {
            content: this.$t('冲突校验', { prop: 'IP' }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'zk_ip',
              type: 'zk_hosts',
            }),
          },
        ],
      },
      {
        prop: 'zk_port',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Zookeeper主机的端口号'),
        rules: [
          {
            content: this.$t('数字0_65535'),
            validator: (value: string) => {
              if (!value) return true;
              let portValidate =  /^[0-9]*$/.test(value);
              if (portValidate) {
                portValidate = parseInt(value, 10) <= 65535;
              }
              return portValidate;
            },
          },
          {
            content: this.$t('冲突校验', { prop: this.$t('端口') }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'zk_port',
              type: 'zk_hosts',
            }),
          },
        ],
      },
    ],
    btfileserver: [
      {
        prop: 'inner_ip',
        classExt: 'ip-input ip-input-inner',
        required: true,
        placeholder: window.i18n.t('请输入Server的内网IP', { type: 'Btfile' }),
        rules: [
          {
            regx: ipRegExp,
            content: this.$t('IP格式不正确'),
          },
          {
            content: this.$t('冲突校验', { prop: 'IP' }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'inner_ip',
              type: 'btfileserver',
            }),
          },
        ],
      },
      {
        prop: 'outer_ip',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Server的外网IP', { type: 'Btfile' }),
        rules: [
          {
            regx: ipRegExp,
            content: this.$t('IP格式不正确'),
          },
          {
            content: this.$t('冲突校验', { prop: 'IP' }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'outer_ip',
              type: 'btfileserver',
            }),
          },
        ],
      },
    ],
    dataserver: [
      {
        prop: 'inner_ip',
        classExt: 'ip-input ip-input-inner',
        required: true,
        placeholder: window.i18n.t('请输入Server的内网IP', { type: 'Data' }),
        rules: [
          {
            regx: ipRegExp,
            content: this.$t('IP格式不正确'),
          },
          {
            content: this.$t('冲突校验', { prop: 'IP' }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'inner_ip',
              type: 'dataserver',
            }),
          },
        ],
      },
      {
        prop: 'outer_ip',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Server的外网IP', { type: 'Data' }),
        rules: [
          {
            regx: ipRegExp,
            content: this.$t('IP格式不正确'),
          },
          {
            content: this.$t('冲突校验', { prop: 'IP' }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'outer_ip',
              type: 'dataserver',
            }),
          },
        ],
      },
    ],
    taskserver: [
      {
        prop: 'inner_ip',
        classExt: 'ip-input ip-input-inner',
        required: true,
        placeholder: window.i18n.t('请输入Server的内网IP', { type: 'Task' }),
        rules: [
          {
            regx: ipRegExp,
            content: this.$t('IP格式不正确'),
          },
          {
            content: this.$t('冲突校验', { prop: 'IP' }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'inner_ip',
              type: 'taskserver',
            }),
          },
        ],
      },
      {
        prop: 'outer_ip',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Server的外网IP', { type: 'Task' }),
        rules: [
          {
            regx: ipRegExp,
            content: this.$t('IP格式不正确'),
          },
          {
            content: this.$t('冲突校验', { prop: 'IP' }),
            validator: (value: string, index: number) => this.validateUnique(value, {
              index,
              prop: 'outer_ip',
              type: 'taskserver',
            }),
          },
        ],
        nginxPath: [
          {
            validator(val: string) {
              return !val || /^(\/[A-Za-z0-9_-]{1,32}){2,}$/.test(val);
            },
            message: this.$t('路径格式不正确', { num: 32 }),
            trigger: 'blur',
          },
          {
            validator: (val: string) => {
              const path = `${val}/`;
              return !this.linuxNotInclude.find(item => path.search(item) > -1);
            },
            message: () => this.$t('不能以如下内容开头', { path: this.linuxNotIncludeError.join(', ') }),
            trigger: 'blur',
          },
        ],
      },
    ],
  };
  private urlReg = /^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w.-]+)+[\w\-._~:/?#[\]@!$&'*+,;=.]+$/;
  // 目录名可以包含但不相等，所以末尾加了 /, 校验的时候给值也需要加上 /
  private linuxNotInclude: string[] = [
    '/etc/', '/root/', '/boot/', '/dev/', '/sys/', '/tmp/', '/var/', '/usr/lib/',
    '/usr/lib64/', '/usr/include/', '/usr/local/etc/', '/usr/local/sa/', '/usr/local/lib/',
    '/usr/local/lib64/', '/usr/local/bin/', '/usr/local/libexec/', '/usr/local/sbin/',
  ];
  private linuxNotIncludeError: string[] = [
    '/etc', '/root', '/boot', '/dev', '/sys', '/tmp', '/var', '/usr/lib',
    '/usr/lib64', '/usr/include', '/usr/local/etc', '/usr/local/sa', '/usr/local/lib',
    '/usr/local/lib64', '/usr/local/bin', '/usr/local/libexec', '/usr/local/sbin',
  ];
  private rules = {
    required: [
      {
        required: true,
        message: this.$t('必填项'),
        trigger: 'blur',
      },
    ],
    name: [
      {
        required: true,
        message: this.$t('必填项'),
        trigger: 'blur',
      },
      {
        validator: (val: string) => /^[A-Za-z0-9_\u4e00-\u9fa5]{3,32}$/.test(val),
        message: this.$t('长度为3_32的字符'),
        trigger: 'blur',
      },
    ],
    url: [
      {
        required: true,
        message: this.$t('必填项'),
        trigger: 'blur',
      },
      {
        validator: (val: string) => this.urlReg.test(val),
        message: this.$t('URL格式不正确'),
        trigger: 'blur',
      },
    ],
    callback: [
      {
        validator: (val: string) => !val || (this.urlReg.test(val) && /(\/backend)$/.test(val)),
        message: this.$t('请输入以backend结尾的URL地址'),
        trigger: 'blur',
      },
    ],
  };
  private labelWidth = 170;

  private get detail() {
    return ConfigStore.apDetail;
  }
  // 动态表单类型内容宽度
  private get relatedContentWidth() {
    // 580: 两个输入框宽度
    return this.labelWidth + 580;
  }
  // 动态表单类型第一个item宽度
  private get firstRelatedInputWidth() {
    // 285: 输入框的宽度
    return this.labelWidth + 285;
  }
  private get zkPasswordType() {
    if (!isEmpty(this.formData.zk_password)) {
      return 'password';
    }
    return 'text';
  }

  @Watch('formData', { deep: true })
  private formDataChange() {
    if (this.isInit) { // 第二步到第一步的时候保持检查结果为通过
      this.isInit = false;
    } else {
      this.checkedResult = false;
    }
  }
  private mounted() {
    this.initDetail();
    this.checkedResult = this.stepCheck;
    this.labelWidth = this.initLabelWidth(this.formDataRef) || 0;
  }

  private initDetail() {
    Object.keys(this.formData).forEach((key) => {
      if (this.detail[key as keyof IApBase]) {
        this.formData[key as keyof IApBase] = key === 'zk_hosts' || /server/g.test(key)
          ? JSON.parse(JSON.stringify(this.detail[key as keyof IApBase])) : this.detail[key as keyof IApBase];
      }
    });
  }
  private checkCommit() {
    this.formDataRef.validate().then(() => {
      this.validate(async () => {
        this.checkLoading = true;
        const { btfileserver, dataserver, taskserver, package_inner_url, package_outer_url } = this.formData;
        const data = await ConfigStore.requestCheckUsability({
          btfileserver, dataserver, taskserver, package_inner_url, package_outer_url,
        });
        this.checkedResult = !!data.test_result;
        this.checkedResultList = data.test_logs || [];
        this.isChecked = true;
        this.checkLoading = false;
      });
    }, () => {
      this.validate(null);
    });
  }
  private submitInfo() {
    ConfigStore.updateDetail(this.formData);
    this.$emit('change', true);
    this.$emit('step');
  }
  private addAddress(index: number, type: 'zk_hosts'| IServer) {
    if (this.checkLoading) return;
    if (type === 'zk_hosts') {
      this.formData[type].splice(index + 1, 0, { zk_ip: '', zk_port: '' });
    } else {
      this.formData[type].splice(index + 1, 0, { inner_ip: '', outer_ip: '' });
    }
  }
  private deleteAddress(index: number, type: 'zk_hosts'| IServer) {
    if (this.formData[type].length <= 1) return;
    this.formData[type].splice(index, 1);
  }
  private cancel() {
    this.$router.push({
      name: 'gseConfig',
    });
  }
  /**
   * 外部调用的校验方法
   */
  private validate(callback: Function | null) {
    return new Promise((resolve, reject) => {
      let isValidate = true;
      let count = 0;
      // eslint-disable-next-line @typescript-eslint/no-this-alias
      const that = this;
      // 调用各个组件内部校验方法
      Object.values(this.checkItem).forEach((instance) => {
        instance.handleValidate((validator: { show: boolean }) => {
          if (validator.show) {
            isValidate = false;
            reject(validator);
            return false;
          }
          count += 1;
          if (count === that.checkItem.length) {
            resolve(isValidate);
            if (typeof callback === 'function') {
              callback(isValidate);
            }
          }
        });
      });
    });
  }
  private getDefaultValidator() {
    return {
      show: false,
      content: '',
      errTag: true,
    };
  }
  private validateUnique(value: string, { prop, type, index }: { prop: string, type: string, index: number }) {
    let repeat = false;
    if (!this.formData[type as keyof IApBase]) return !repeat;
    if (['zk_port', 'zk_ip'].includes(prop)) {
      const negateProp = prop === 'zk_ip' ? 'zk_port' : 'zk_ip';
      const zk = this.formData.zk_hosts[index];
      if (isEmpty(zk[negateProp])) {
        return !repeat;
      }
      // zk_host校验 ip + port 不相等
      repeat = this.formData[type as 'zk_hosts'].some((item: IZk, i: number) => i !== index
                && (item.zk_ip + item.zk_port === zk.zk_ip + zk.zk_port));
    } else {
      // eslint-disable-next-line vue/max-len
      repeat = this.formData[type as IServer].some((item: IIpGroup, i: number) => i !== index
        && item[prop as keyof IIpGroup] === value);
    }
    return !repeat;
  }
  private hadleFormChange() {
    MainStore.updateEdited(true);
  }
}
</script>

<style lang="postcss" scoped>
@import "@/css/variable.css";

>>> .bk-form-content .bk-form-control {
  width: 580px;
}
.access-point-host {
  .bg-white {
    background: $whiteColor;
  }
  /deep/ .textarea-description .bk-limit-box {
    line-height: 1;
  }
  .check-result {
    position: relative;
    padding-top: 10px;
    width: 580px;
    &:before {
      position: absolute;
      top: 6px;
      left: 108px;
      display: block;
      width: 5px;
      height: 5px;
      content: "";
      border: 1px solid #dcdee5;
      border-left-color: transparent;
      border-bottom-color: transparent;
      background: #f0f1f5;
      transform: rotateZ(-45deg);
    }
  }
  .check-result-detail {
    padding: 15px 20px;
    min-height: 125px;
    max-height: 500px;
    line-height: 24px;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    font-size: 12px;
    color: #63656e;
    background: #f0f1f5;
    overflow-y: auto;
    .result-title {
      margin: 0;
    }
    .success {
      color: #2dcb56;
    }
    .error {
      color: #ea3636;
    }
  }
  .setup-body {
    background: #fff;
    tr {
      height: 44px;
      td {
        padding: 0 5px;
        &:first-child {
          padding-left: 16px;
        }
      }
    }
  }
  .ip-related-item {
    position: relative;
    .bk-label {
      line-height: 44px;
    }
    >>> .bk-form-content .bk-form-control {
      width: auto;
    }
  }
  .ip-input-outer {
    /deep/ .bk-label {
      display: none;
    }
    /deep/ .bk-form-content {
      /* stylelint-disable-next-line declaration-no-important */
      margin: 0 !important;
    }
  }
  .opera-icon-group {
    display: flex;
    align-items: center;
    height: 32px;
    font-size: 18px;
    color: #c4c6cc;
    i {
      cursor: pointer;
      &:hover {
        color: #979ba5;
      }
      & + i {
        margin-left: 10px;
      }
      &.disable-icon {
        color: #dcdee5;
        cursor: not-allowed;
      }
    }
  }
  .check-btn {
    min-width: 216px;
  }
}
</style>
