<template>
  <div class="access-point-host">
    <bk-form v-test="'apBaseForm'" :label-width="hostState.labelWidth" :model="formData" ref="formDataRef">
      <template v-for="(formItem, itemIndex) in hostState.formList">
        <!-- zk&server - table -->
        <template v-if="formItem.type === 'zk'">
          <!-- Zookeeper -->
          <div
            :style="{ width: `${relatedContentWidth}px` }"
            class="bk-form-item ip-related-item clearfix mb40"
            :key="itemIndex">
            <div class="bk-form-item is-required">
              <label class="bk-label" :style="{ width: `${ hostState.labelWidth }px` }">
                <span class="bk-label-text">Zookeeper</span>
              </label>
              <div class="bk-form-content" :style="{ 'margin-left': `${ hostState.labelWidth }px` }">
                <SetupFormTable :table-head="checkConfig.zkHead" v-test="'apBaseTable'">
                  <tbody class="setup-body" slot="tbody">
                    <tr v-for="(host, index) in formData.zk_hosts" :key="`zk_hosts_td_${index}`">
                      <td>{{ index + 1 }}</td>
                      <HostTdInput
                        ref="checkItem"
                        v-for="(config, idx) in checkConfig.zk_hosts"
                        :key="`zk_hosts_td_${idx}`"
                        :disabled="hostState.checkLoading"
                        :rules="config.rules"
                        v-model="host[config.prop]">
                      </HostTdInput>
                      <HostTdOperate
                        :add-disabled="hostState.checkLoading"
                        :delete-disabled="formData.zk_hosts.length <= 1"
                        @add="() => addAddress(index, 'zk_hosts')"
                        @delete="() => deleteAddress(index, 'zk_hosts')">
                      </HostTdOperate>
                    </tr>
                  </tbody>
                </SetupFormTable>
              </div>
            </div>
          </div>
          <div
            v-for="(label, labelIndex) in labelTableList" :key="`${itemIndex}_${labelIndex}`"
            :style="{ width: `${relatedContentWidth}px` }"
            class="bk-form-item ip-related-item clearfix mb24">
            <div class="bk-form-item is-required">
              <label class="bk-label" :style="{ width: `${ hostState.labelWidth }px` }">
                <span class="bk-label-text">{{label.name}}</span>
              </label>
              <div class="bk-form-content" :style="{ 'margin-left': `${ hostState.labelWidth }px` }">
                <SetupFormTable :table-head="checkConfig.innerHead" v-test="'apBaseTable'">
                  <tbody class="setup-body" slot="tbody">
                    <tr
                      v-for="(host, index) in formData[label.key].inner_ip_infos"
                      :key="`${label.key}td_inner_${index}`">
                      <td>{{ index + 1 }}</td>
                      <HostTdInput
                        ref="checkItem"
                        :disabled="hostState.checkLoading"
                        :rules="checkConfig[label.key][0].rules"
                        v-model="host.ip" />
                      <HostTdOperate
                        :add-disabled="hostState.checkLoading"
                        :delete-disabled="formData[label.key].inner_ip_infos.length <= 1"
                        @add="() => addAddress(index, label.key, 'inner_ip_infos')"
                        @delete="() => deleteAddress(index, label.key, 'inner_ip_infos')">
                      </HostTdOperate>
                    </tr>
                  </tbody>
                </SetupFormTable>
              </div>
            </div>
            <div class="bk-form-item">
              <label class="bk-label" :style="{ width: `${ hostState.labelWidth }px` }">
                <span class="bk-label-text"></span>
              </label>
              <div class="bk-form-content" :style="{ 'margin-left': `${ hostState.labelWidth }px` }">
                <SetupFormTable :table-head="checkConfig.outerHead" v-test="'apBaseTable'">
                  <tbody class="setup-body" slot="tbody">
                    <tr
                      v-for="(host, index) in formData[label.key].outer_ip_infos"
                      :key="`${label.key}td_outerer_${index}`">
                      <td>{{ index + 1 }}</td>
                      <HostTdInput
                        ref="checkItem"
                        :disabled="hostState.checkLoading"
                        :rules="checkConfig[label.key][1].rules"
                        v-model="host.ip" />
                      <HostTdOperate
                        :add-disabled="hostState.checkLoading"
                        :delete-disabled="formData[label.key].outer_ip_infos.length <= 1"
                        @add="() => addAddress(index, label.key, 'outer_ip_infos')"
                        @delete="() => deleteAddress(index, label.key, 'outer_ip_infos')">
                      </HostTdOperate>
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
            :loading="hostState.checkLoading"
            :disabled="hostState.checkedResult"
            v-test="'apTestBtn'"
            @click.stop="checkCommit">
            {{ $t('测试Server及URL可用性') }}
          </bk-button>
          <bk-button
            class="ml30"
            theme="primary"
            v-test="'apOmitBtn'"
            @click.stop="() => hostState.checkedResult = true">
            {{ $t('跳过检测') }}
          </bk-button>
          <section class="check-result" v-if="hostState.isChecked">
            <div class="check-result-detail">
              <template v-if="hostState.isChecked">
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
          <InstallInputType
            class="zk-pwd-item"
            type="password"
            :placeholder="$t('请输入')"
            v-model.trim="formData.zk_password"
            :pwd-fill="detail.pwsFill"
            @change="hadleFormChange" />
        </bk-form-item>

        <template v-else-if="formItem.type === 'url'">
          <bk-form-item
            v-for="opt in formItem.items" :key="opt.key"
            :class="opt.extCls"
            :label="opt.label"
            :required="opt.required"
            :rules="hostState.rules[opt.ruleName]"
            :property="opt.key"
            error-display-type="normal">
            <bk-input
              v-test="`apBaseInput.${opt.key}`"
              type="text"
              :placeholder="opt.placeholder"
              v-model.trim="formData[opt.key]"
              @change="hadleFormChange">
              <template slot="prepend">
                <div class="group-text">{{ opt.prepend }}</div>
              </template>
            </bk-input>
          </bk-form-item>
        </template>

        <bk-form-item
          v-else
          :class="formItem.extCls"
          :key="itemIndex"
          :label="formItem.label"
          :required="formItem.required"
          :rules="hostState.rules[formItem.ruleName]"
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
          :disabled="!hostState.checkedResult || hostState.checkLoading"
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


<script lang="ts" setup>
import { getCurrentInstance, toRefs, computed, onMounted, reactive, ref, watch } from 'vue';
import { MainStore, ConfigStore } from '@/store/index';
import i18n from '@/setup';
import { IServerProp, IApBase, IAvailable, IZk } from '@/types/config/config';
import InstallInputType from '@/components/setup-table/install-input-type.vue';
import useFormLabelWidth from '@/common/form-label-hook';
import SetupFormTable from './step-form-table.vue';
import HostTdInput from './host-td-input.vue';
import HostTdOperate from './host-td-operate.vue';
import { isEmpty } from '@/common/util';
import { stepHost, linuxNotInclude, linuxNotIncludeError } from './apFormConfig';
import { regUrlMixinIp, regFnSysPath, regIp, regIPv6 } from '@/common/regexp';
import { reguRequired, reguUrlMixinIp, reguPort, reguFnName, reguIPMixins } from '@/common/form-check';
import { TranslateResult } from 'vue-i18n';

type IServer = 'btfileserver' | 'dataserver' | 'taskserver';
type ApBase = keyof IApBase;
type IpInfo = 'inner_ip_infos' | 'outer_ip_infos';

const proxy = getCurrentInstance()?.proxy as Vue;

const emits = defineEmits(['change', 'step']);

const props = withDefaults(defineProps<{
  pointId: string | number;
  stepCheck: boolean;
  isEdit: boolean;
}>(), {
  pointId: '',
  stepCheck: false,
  isEdit: false,
});

const formDataRef = ref<any>();
const checkItem = ref<any[]>([]);

const { initLabelWidth } = useFormLabelWidth();

const checkedResultList = ref<{
  log_level: string;
  log: string;
}[]>([]);

const formData = ref<IApBase>({
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
  btfileserver: {
    inner_ip_infos: [{ ip: '' }],
    outer_ip_infos: [{ ip: '' }],
  },
  dataserver: {
    inner_ip_infos: [{ ip: '' }],
    outer_ip_infos: [{ ip: '' }],
  },
  taskserver: {
    inner_ip_infos: [{ ip: '' }],
    outer_ip_infos: [{ ip: '' }],
  },
  callback_url: '',
  outer_callback_url: '',
  package_inner_url: '',
  package_outer_url: '',
  nginx_path: '',
});


const hostState = reactive({
  checkLoading: false,
  isInit: true,
  checkedResult: false,
  isChecked: false,
  formList: stepHost,
  labelWidth: 170,
  linuxPathReg: regFnSysPath({ maxText: 32, minLevel: 2 }),
  rules: {
    required: [reguRequired],
    name: [reguRequired, reguFnName()],
    url: [reguRequired, reguUrlMixinIp],
    callback: [
      {
        validator: (val: string) => !val || regUrlMixinIp.test(val),
        message: i18n.t('URL格式不正确'),
        // validator: (val: string) => !val || (regUrl.test(val) && /(\/backend)$/.test(val)),
        // message: i18n.t('请输入以backend结尾的URL地址'),
        trigger: 'blur',
      },
    ],
  },
});

const labelTableList = ref<{
  name: TranslateResult;
  key: 'btfileserver' | 'dataserver' | 'taskserver';
  // key: 'zk_hosts' | 'btfileserver' | 'dataserver' | 'taskserver';
  thead: 'zkHead'| 'head';
}[]>([
  // { name: 'Zookeeper', key: 'zk_hosts', thead: 'zkHead' },
  { name: i18n.t('GSEFile服务地址'), key: 'btfileserver', thead: 'head' },
  { name: i18n.t('GSEData服务地址'), key: 'dataserver', thead: 'head' },
  { name: i18n.t('GSECluster服务地址'), key: 'taskserver', thead: 'head' },
]);
const checkConfig = ref({
  zkHead: [
    { name: i18n.t('序号'), width: 70 },
    { name: 'IP', width: 230 },
    { name: 'PORT', width: 230 },
    { name: '', width: 70 },
  ],
  innerHead: [
    { name: i18n.tc('序号'), width: 70 },
    { name: i18n.t('内网IP'), width: 460 },
    { name: '', width: 70 },
  ],
  outerHead: [
    { name: i18n.tc('序号'), width: 70 },
    { name: i18n.t('外网IP'), width: 460 },
    { name: '', width: 70 },
  ],
  zk_hosts: [
    {
      prop: 'zk_ip',
      classExt: 'ip-input ip-input-inner',
      required: true,
      placeholder: i18n.t('请输入Zookeeper主机的IP'),
      rules: [reguIPMixins, ipConflictRule('zk_ip', 'zk_hosts')],
    },
    {
      prop: 'zk_port',
      classExt: 'ip-input ip-input-outer',
      placeholder: i18n.t('请输入Zookeeper主机的端口号'),
      rules: [reguPort, ipConflictRule('zk_port', 'zk_hosts')],
    },
  ],
  btfileserver: [
    {
      prop: 'inner_ip',
      classExt: 'ip-input ip-input-inner',
      required: true,
      placeholder: i18n.t('请输入Server的内网IP', { type: 'Btfile' }),
      rules: [reguIPMixins, ipConflictRule('inner_ip_infos', 'btfileserver'), ipSameTypeRule('inner_ip_infos', 'btfileserver')],
    },
    {
      prop: 'outer_ip',
      classExt: 'ip-input ip-input-outer',
      required: true,
      placeholder: i18n.t('请输入Server的外网IP', { type: 'Btfile' }),
      rules: [reguIPMixins, ipConflictRule('outer_ip_infos', 'btfileserver'), ipSameTypeRule('outer_ip_infos', 'btfileserver')],
    },
  ],
  dataserver: [
    {
      prop: 'inner_ip',
      classExt: 'ip-input ip-input-inner',
      required: true,
      placeholder: i18n.t('请输入Server的内网IP', { type: 'Data' }),
      rules: [reguIPMixins, ipConflictRule('inner_ip_infos', 'dataserver'), ipSameTypeRule('inner_ip_infos', 'dataserver')],
    },
    {
      prop: 'outer_ip',
      classExt: 'ip-input ip-input-outer',
      required: true,
      placeholder: i18n.t('请输入Server的外网IP', { type: 'Data' }),
      rules: [reguIPMixins, ipConflictRule('outer_ip_infos', 'dataserver'), ipSameTypeRule('outer_ip_infos', 'dataserver')],
    },
  ],
  taskserver: [
    {
      prop: 'inner_ip',
      classExt: 'ip-input ip-input-inner',
      required: true,
      placeholder: window.i18n.t('请输入Server的内网IP', { type: 'Task' }),
      rules: [reguIPMixins, ipConflictRule('inner_ip_infos', 'taskserver'), ipSameTypeRule('inner_ip_infos', 'taskserver')],
    },
    {
      prop: 'outer_ip',
      classExt: 'ip-input ip-input-outer',
      required: true,
      placeholder: window.i18n.t('请输入Server的外网IP', { type: 'Task' }),
      rules: [reguIPMixins, ipConflictRule('outer_ip_infos', 'taskserver'), ipSameTypeRule('outer_ip_infos', 'taskserver')],
      nginxPath: [
        {
          validator(val: string) {
            return !val || this.linuxPathReg.test(val);
          },
          message: i18n.t('路径格式不正确', { num: 32 }),
          trigger: 'blur',
        },
        {
          validator: (val: string) => {
            const path = `${val}/`;
            return !linuxNotInclude.find(item => path.search(item) > -1);
          },
          message: () => i18n.t('不能以如下内容开头', { path: linuxNotIncludeError.join(', ') }),
          trigger: 'blur',
        },
      ],
    },
  ],
});

const detail = computed(() => ConfigStore.apDetail);
// 动态表单类型内容宽度
const relatedContentWidth = computed(() => hostState.labelWidth + 580); // 580: 两个输入框宽度

const initDetail = () => {
  Object.keys(formData.value).forEach((key: IApBase) => {
    if (detail.value[key]) {
      formData.value[key] = key === 'zk_hosts' || /server/g.test(key)
        ? JSON.parse(JSON.stringify(detail.value[key])) as any
        : detail.value[key];
    }
  });
};
const checkCommit = () => {
  formDataRef.value?.validate?.().then(() => {
    validate(async () => {
      hostState.checkLoading = true;
      const {
        btfileserver, dataserver, taskserver,
        package_inner_url, package_outer_url, callback_url, outer_callback_url,
      } = formData.value;
      const params: IAvailable = {
        btfileserver, dataserver, taskserver, package_inner_url, package_outer_url,
      };
      if (callback_url) {
        params.callback_url = callback_url;
      }
      if (outer_callback_url) {
        params.outer_callback_url = outer_callback_url;
      }
      const data = await ConfigStore.requestCheckUsability(params);
      hostState.checkedResult = !!data.test_result;
      checkedResultList.value = data.test_logs || [];
      hostState.isChecked = true;
      hostState.checkLoading = false;
    }).catch(() => document.getElementsByClassName('is-error')[0]?.scrollIntoView());
  }, () => document.getElementsByClassName('is-error')[0]?.scrollIntoView());
};
const submitInfo = () => {
  ConfigStore.updateDetail(formData.value);
  emits('change', true);
  emits('step');
};
const addAddress = (index: number, type: 'zk_hosts'| IServer, prop?: IServerProp) => {
  if (hostState.checkLoading) return;
  if (type === 'zk_hosts') {
    formData.value[type].splice(index + 1, 0, { zk_ip: '', zk_port: '' });
  } else {
    formData.value[type][prop as IServerProp].splice(index + 1, 0, { ip: '' });
  }
};
const deleteAddress = (index: number, type: 'zk_hosts'| IServer, prop?: 'inner_ip_infos' | 'outer_ip_infos') => {
  if (type === 'zk_hosts') {
    if (formData.value[type].length <= 1) return;
    formData.value[type].splice(index, 1);
  } else {
    if (formData.value[type][prop as IServerProp].length <= 1) return;
    formData.value[type][prop as IServerProp].splice(index, 1);
  }
};
const cancel = () => {
  proxy.$router.push({
    name: 'gseConfig',
  });
};
/**
 * 外部调用的校验方法
 */
const validate = (callback: Function | null) => new Promise((resolve, reject) => {
  let isValidate = true;
  let count = 0;
  const len = checkItem.value.length;
  // 调用各个组件内部校验方法
  Object.values(checkItem.value).forEach((instance) => {
      instance.handleValidate?.((validator: { show: boolean }) => {
        if (validator.show) {
          isValidate = false;
          reject(validator);
          return false;
        }
        count += 1;
        if (count === len) {
          resolve(isValidate);
          if (typeof callback === 'function') {
            callback(isValidate);
          }
        }
      });
  });
});
const getDefaultValidator = () => ({
  show: false,
  message: '',
  errTag: true,
});
function ipConflictRule(prop: string, type: string) {
  return {
    message: i18n.t('冲突校验', { prop: 'IP' }),
    validator: (value: string) => validateUnique(value, { prop, type }),
  };
}
const validateUnique = (value: string, { prop, type }: { prop: string, type: string }) => {
  let repeat = false;
  if (!formData.value[type as ApBase]) return !repeat;
  if (['zk_port', 'zk_ip'].includes(prop)) {
    const negateProp = prop === 'zk_ip' ? 'zk_port' : 'zk_ip';
    const zk = formData.value.zk_hosts[0];
    if (isEmpty(zk[negateProp])) {
      return !repeat;
    }
    // zk_host校验 ip + port 不相等
    repeat = formData.value[type as 'zk_hosts'].some((item: IZk, i: number) => i !== 0
              && (item.zk_ip + item.zk_port === zk.zk_ip + zk.zk_port));
  } else {
    // eslint-disable-next-line vue/max-len
    repeat = formData.value[type as IServer][prop as IpInfo]
      .filter((item: { ip: string }) => item.ip === value).length >= 2;
  }
  return !repeat;
};
// IPv4和IPv6二选一
function ipSameTypeRule(prop: IpInfo, type: IServer) {
  return {
    message: i18n.t('IPv4和IPv6不能混合使用'),
    validator: (value: string) => {
      const ips: string[] = formData.value[type][prop].map((item: { ip: string }) => item.ip);
      const isIPv4 = regIp.test(value);
      return ips.length < 2 || (isIPv4
        ? !ips.find(ip => regIPv6.test(ip))
        : !ips.find(ip => regIp.test(ip)));
    },
  };
}
const hadleFormChange = () => {
  MainStore.updateEdited(true);
};

watch(() => formData, () => {
  // 第二步到第一步的时候保持检查结果为通过
  if (hostState.isInit) {
    hostState.isInit = false;
  } else {
    hostState.checkedResult = false;
  }
}, { deep: true });

onMounted(() => {
  initDetail();
  hostState.checkedResult = props.stepCheck;
  hostState.labelWidth = initLabelWidth(formDataRef.value) || 0;
});

defineExpose({
  formDataRef,
  checkItem,
  checkConfig,
  ...toRefs(hostState),
  getDefaultValidator,
});

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
  >>> .textarea-description .bk-limit-box {
    line-height: 1;
  }
  .zk-pwd-item {
    width: 580px;
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
      td:first-child {
        text-align: center;
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
    >>> .bk-label {
      display: none;
    }
    >>> .bk-form-content {
      /* stylelint-disable-next-line declaration-no-important */
      margin: 0 !important;
    }
  }
  .check-btn {
    min-width: 216px;
  }
  .group-text {
    width: 68px;
    padding: 0;
    text-align: center;
  }
  .mb24 {
    margin-bottom: 24px;
  }
}
</style>
