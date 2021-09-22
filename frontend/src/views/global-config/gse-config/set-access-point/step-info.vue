<template>
  <div class="access-point-info">
    <bk-form :label-width="155" :model="formData" ref="formData">
      <template v-for="(system, index) in pathSet">
        <h3 :class="['block-title', { mt40: !index }]" :key="index">{{ system.title }}</h3>
        <bk-form-item
          v-for="(path, itemIndex) in system.children"
          error-display-type="normal"
          :label="path.label"
          :property="path.prop"
          :required="path.required"
          :rules="rules[path.rules]"
          :key="`${system.type}-${itemIndex}`">
          <bk-input
            v-model.trim="formData[path.prop]"
            v-test="`apHostInput.${path.prop}`"
            :placeholder="path.placeholder || $t('请输入')"
            @blur="pathRepair(arguments, path.prop)"
            @change="hadleFormChange">
          </bk-input>
        </bk-form-item>
      </template>
      <h3 class="block-title">{{ $t('Proxy信息') }}</h3>
      <bk-form-item
        v-for="(item, index) in formData.packageList"
        error-display-type="normal"
        :label="!index ? $t('Proxy上的安装包') : ''"
        :required="true"
        :rules="rules.package"
        :property="'packageList.' + index + '.value'"
        :key="`package_${index}`">
        <bk-input v-test="'apHostPackage'" v-model.trim="item.value" @change="hadleFormChange" />
        <div class="opera-icon-group">
          <i
            v-test="'addPackageBtn'"
            :class="['nodeman-icon nc-plus', { 'disable-icon': submitLoading }]"
            @click="handlePackageOperate('add', index)">
          </i>
          <i
            v-test="'deletePackageBtn'"
            :class="['nodeman-icon nc-minus', { 'disable-icon': submitLoading || formData.packageList.length <= 1 }]"
            @click="handlePackageOperate('delete', index)">
          </i>
        </div>
      </bk-form-item>

      <bk-form-item class="mt30 item-button-group">
        <bk-button
          class="nodeman-primary-btn"
          v-test.common="'formCommit'"
          theme="primary"
          :disabled="submitLoading"
          @click.stop.prevent="submitHandle">
          {{ $t('确认') }}
        </bk-button>
        <bk-button
          class="nodeman-cancel-btn"
          :disabled="submitLoading"
          @click="stepNext">
          {{ $t('上一步') }}
        </bk-button>
        <bk-button
          class="nodeman-cancel-btn"
          :disabled="submitLoading"
          @click="cancel">
          {{ $t('取消') }}
        </bk-button>
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Ref } from 'vue-property-decorator';
import { MainStore, ConfigStore } from '@/store/index';
import { IApParams } from '@/types/config/config';
import { transformDataKey, toLine } from '@/common/util';
import { apAgentInfo, apAgentInfoRules } from './apFormConfig';

@Component({ name: 'StepInfo' })

export default class StepInfo extends Vue {
  @Prop({ type: [String, Number], default: '' }) private readonly pointId!: string | number;
  @Prop({ type: Boolean, default: false }) private readonly isEdit!: boolean;

  private submitLoading = false;
  private pathSet = apAgentInfo;
  private rules = apAgentInfoRules;
  private formData: Dictionary = {
    linuxDataipc: '/var/run/ipc.state.report',
    linuxHostidPath: '/var/lib/gse/host/hostid',
    linuxSetupPath: '/usr/local/gse',
    linuxDataPath: '/usr/local/gse',
    linuxRunPath: '/usr/local/gse',
    linuxLogPath: '/usr/log/gse',
    linuxTempPath: '/tmp',
    windowsHostidPath: 'C:\\gse\\data\\host\\hostid',
    windowsDataipc: '',
    windowsSetupPath: 'C:\\gse',
    windowsDataPath: 'C:\\gse',
    windowsRunPath: 'c:\\gse\\run',
    windowsLogPath: 'C:\\gse\\logs',
    windowsTempPath: 'C:\\tmp',
    packageList: [
      { value: '' },
    ],
  };
  @Ref('formData') private readonly formDataRef!: any;

  private get detail() {
    return ConfigStore.apDetail;
  }
  private mounted() {
    this.initConfig();
    // this.initLabelWidth(this.$refs.formData)
  }
  public initConfig() {
    const { agent_config: { linux, windows }, proxy_package: proxyPackage = [] } = this.detail;
    try {
      const dataMap: Dictionary = {};
      Object.keys(linux).forEach((key) => {
        if (this.isEdit || linux[key]) {
          dataMap[`linux_${key}`] = linux[key] || '';
        }
      });
      Object.keys(windows).forEach((key) => {
        // 非编辑模式下不能覆盖默认值
        if (this.isEdit || windows[key]) {
          dataMap[`windows_${key}`] = windows[key] || '';
        }
      });
      const packageList = proxyPackage.reduce((arr: { value: string }[], item: string) => {
        arr.push({ value: item });
        return arr;
      }, []);
      this.formData.packageList.splice(0, packageList.length ? this.formData.packageList.length : 0, ...packageList);
      Object.assign(this.formData, transformDataKey(dataMap));
    } catch (_) {}
  }
  public submitHandle() {
    this.formDataRef.validate().then(async () => {
      const {
        name, zk_account, zk_password, region_id, city_id, zk_hosts, btfileserver, dataserver,
        taskserver, outer_callback_url, package_inner_url, package_outer_url, nginx_path, description,
      } = this.detail;
      this.submitLoading = true;
      const agentConfig: { linux: Dictionary, windows: Dictionary } = {
        linux: {},
        windows: {},
      };
      Object.keys(this.formData).forEach((key) => {
        if (/linux/ig.test(key)) {
          const str = toLine(key).replace(/linux_/g, '');
          agentConfig.linux[str] = this.formData[key];
        }
        if (/windows/ig.test(key)) {
          const str = toLine(key).replace(/windows_/g, '');
          agentConfig.windows[str] = this.formData[key];
        }
      });
      // detail里边多余的字段不能传入，否则通不过后端校验
      const formatData: IApParams = {
        name,
        zk_account,
        zk_password,
        region_id,
        city_id,
        zk_hosts,
        btfileserver,
        dataserver,
        taskserver,
        outer_callback_url,
        package_inner_url,
        package_outer_url,
        nginx_path,
        agent_config: agentConfig,
        description,
        proxy_package: this.formData.packageList.map((item: { value: string }) => item.value),
      };
      if (this.isEdit) {
        if (!(formatData.zk_password || !formatData.zk_account)) {
          delete formatData.zk_password;
        }
      }
      let res;
      if (this.isEdit) {
        res = await ConfigStore.requestEditPoint({ pointId: this.pointId as number, data: formatData });
      } else {
        res = await ConfigStore.requestCreatePoint(formatData);
      }
      this.submitLoading = false;
      if (res) {
        this.$bkMessage({
          theme: 'success',
          message: this.isEdit ? this.$t('修改接入点成功') : this.$t('新增接入点成功'),
        });
        MainStore.updateEdited(false);
        this.cancel();
      }
    }, () => {});
  }
  public stepNext() {
    this.$emit('step', 1);
  }
  public cancel() {
    this.$router.push({
      name: 'gseConfig',
    });
  }
  // 安装路径修复 - 若路径以 / 结尾，则去掉末尾的 /
  public pathRepair(arg: string[], prop: string) {
    const value = arg[0].trim().replace(/[/\\]+/ig, '/');
    const pathArr = value.split('/').filter((item: string) => !!item);
    if (/linux/ig.test(prop)) {
      this.formData[prop] = `/${pathArr.join('/')}`;
    } else {
      if (prop === 'windowsDataipc') {
        return;
      }
      this.formData[prop] = pathArr.join('\\');
    }
  }
  public hadleFormChange() {
    MainStore.updateEdited(true);
  }
  public handlePackageOperate(type: string, index: number) {
    if (this.submitLoading) return;
    if (type === 'add') {
      this.formData.packageList.splice(index + 1, 0, { value: '' });
    } else {
      if (this.formData.packageList.length > 1) {
        this.formData.packageList.splice(index, 1);
      }
    }
  }
}
</script>

<style lang="postcss" scoped>

.access-point-info {
  /deep/ form {
    width: 740px;
  }
  .block-title {
    margin: 30px 0 20px 0;
    padding: 0 0 10px 0;
    border-bottom: 1px solid #dcdee5;
    font-size: 14px;
    font-weight: bold;
  }
  .opera-icon-group {
    position: absolute;
    top: 0;
    left: 100%;
    margin-left: 12px;
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
}
</style>
