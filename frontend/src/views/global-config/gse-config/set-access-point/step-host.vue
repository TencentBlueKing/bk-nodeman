<template>
  <div class="access-point-host">
    <bk-form v-test="'apBaseForm'" :label-width="labelWidth" :model="formData" ref="formData">
      <template v-for="(formItem, itemIndex) in formList">
        <!-- zk&server - table -->
        <template v-if="formItem.type === 'zk'">
          <div
            v-for="(label, labelIndex) in labelTableList" :key="`${itemIndex}_${labelIndex}`"
            :style="{ width: `${relatedContentWidth}px` }"
            :class="['bk-form-item ip-related-item clearfix', { mb40: !labelIndex }]">
            <div class="bk-form-item is-required">
              <label class="bk-label" :style="{ width: `${ labelWidth }px` }">
                <span class="bk-label-text">{{label.name}}</span>
              </label>
              <div class="bk-form-content" :style="{ 'margin-left': `${ labelWidth }px` }">
                <SetupFormTable :table-head="checkConfig[label.thead]" v-test="'apBaseTable'">
                  <tbody class="setup-body" slot="tbody">
                    <tr v-for="(host, index) in formData[label.key]" :key="`${label.key}td${index}`">
                      <td>{{ index + 1 }}</td>
                      <td
                        class="is-required"
                        v-for="(config, idx) in checkConfig[label.key]"
                        :key="`${label.key}td${idx}`">
                        <VerifyInput
                          position="right"
                          ref="checkItem"
                          required
                          :rules="config.rules"
                          :id="index"
                          :default-validator="getDefaultValidator()">
                          <InputType
                            v-test="'apBaseInput'"
                            v-model.trim="host[config.prop]"
                            v-bind="{ type: 'text', placeholder: $t('请输入'), disabled: checkLoading }"
                            @change="hadleFormChange">
                          </InputType>
                        </VerifyInput>
                      </td>
                      <td>
                        <div class="opera-icon-group">
                          <i
                            v-test="'addRowBtn'"
                            :class="['nodeman-icon nc-plus', { 'disable-icon': checkLoading }]"
                            @click="addAddress(index, label.key)">
                          </i>
                          <i
                            v-test="'deleteRowBtn'"
                            :class="['nodeman-icon nc-minus', { 'disable-icon': formData[label.key].length <= 1 }]"
                            @click="deleteAddress(index, label.key)">
                          </i>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </SetupFormTable>
              </div>
            </div>
          </div>
        </template>
        <!-- 可用性测试 -->
        <bk-form-item :key="itemIndex" class="mt30" v-else-if="formItem.type === 'usability'">
          <bk-button
            class="check-btn"
            theme="primary"
            :loading="checkLoading"
            :disabled="checkedResult"
            v-test="'apTestBtn'"
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

        <bk-form-item
          v-else-if="formItem.type === 'zkPassword'"
          :key="itemIndex"
          :label="$t('Zookeeper密码')"
          property="zk_password">
          <bk-input
            :type="zkPasswordType"
            :placeholder="$t('请输入')"
            v-model.trim="formData.zk_password"
            @change="hadleFormChange">
          </bk-input>
        </bk-form-item>

        <bk-form-item
          v-else
          :class="formItem.extCls"
          :key="itemIndex"
          :label="formItem.label"
          :required="formItem.required"
          :rules="rules[formItem.ruleName]"
          :property="formItem.key"
          error-display-type="normal">
          <bk-input
            v-test="`apBaseInput.${formItem.key}`"
            :ext-cls="formItem.inputExtCls"
            :type="formItem.type || 'text'"
            :placeholder="formItem.placeholder"
            :rows="formItem.rows"
            :maxlength="formItem.maxLength"
            v-model.trim="formData[formItem.key]"
            @change="hadleFormChange">
          </bk-input>
        </bk-form-item>
      </template>

      <bk-form-item class="item-button-group mt30">
        <bk-button
          class="nodeman-primary-btn"
          theme="primary"
          :disabled="!checkedResult || checkLoading"
          v-test.common="'formCommit'"
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
import { stepHost } from './apFormConfig';
import { regUrl, reguRequired, reguUrl, reguIp, reguPort, regFnSysPath, reguFnName } from '@/common/form-check';

type IServer = 'btfileserver' | 'dataserver' | 'taskserver';

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
  private formList = stepHost;
  private linuxPathReg = regFnSysPath({ maxText: 32, minLevel: 2 });
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
        rules: [reguIp, this.ipConflictRule('zk_ip', 'zk_hosts'),
        ],
      },
      {
        prop: 'zk_port',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Zookeeper主机的端口号'),
        rules: [reguPort, this.ipConflictRule('zk_port', 'zk_hosts')],
      },
    ],
    btfileserver: [
      {
        prop: 'inner_ip',
        classExt: 'ip-input ip-input-inner',
        required: true,
        placeholder: window.i18n.t('请输入Server的内网IP', { type: 'Btfile' }),
        rules: [reguIp, this.ipConflictRule('inner_ip', 'btfileserver')],
      },
      {
        prop: 'outer_ip',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Server的外网IP', { type: 'Btfile' }),
        rules: [reguIp, this.ipConflictRule('outer_ip', 'btfileserver')],
      },
    ],
    dataserver: [
      {
        prop: 'inner_ip',
        classExt: 'ip-input ip-input-inner',
        required: true,
        placeholder: window.i18n.t('请输入Server的内网IP', { type: 'Data' }),
        rules: [reguIp, this.ipConflictRule('inner_ip', 'dataserver')],
      },
      {
        prop: 'outer_ip',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Server的外网IP', { type: 'Data' }),
        rules: [reguIp, this.ipConflictRule('outer_ip', 'dataserver')],
      },
    ],
    taskserver: [
      {
        prop: 'inner_ip',
        classExt: 'ip-input ip-input-inner',
        required: true,
        placeholder: window.i18n.t('请输入Server的内网IP', { type: 'Task' }),
        rules: [reguIp, this.ipConflictRule('inner_ip', 'taskserver')],
      },
      {
        prop: 'outer_ip',
        classExt: 'ip-input ip-input-outer',
        placeholder: window.i18n.t('请输入Server的外网IP', { type: 'Task' }),
        rules: [reguIp, this.ipConflictRule('outer_ip', 'taskserver')],
        nginxPath: [
          {
            validator(val: string) {
              return !val || this.linuxPathReg.test(val);
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
    required: [reguRequired],
    name: [reguRequired, reguFnName()],
    url: [reguRequired, reguUrl],
    callback: [
      {
        validator: (val: string) => !val || (regUrl.test(val) && /(\/backend)$/.test(val)),
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
      message: '',
      errTag: true,
    };
  }
  private ipConflictRule(prop: string, type: string) {
    return {
      message: this.$t('冲突校验', { prop: 'IP' }),
      validator: (value: string, index: number) => this.validateUnique(value, { index, prop, type }),
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
