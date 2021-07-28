<template>
  <section class="bk-plugin-operation">
    <div class="operat-container">

      <div class="form-item">
        <div class="form-item-left">
          <span>{{ $t('选择操作') }}：</span>
        </div>
        <div class="form-item-right">
          <div class="bk-button-group">
            <bk-button
              v-for="(item, index) in operateList"
              :key="index"
              ext-cls="btn-item"
              :class="formData.jobType === item.id ? 'is-selected' : ''"
              @click="changeOperation(item, index)">
              {{ item.name }}
            </bk-button>
          </div>
        </div>
      </div>

      <div class="form-item" v-if="isUpdate">
        <div class="form-item-left">
          <span>{{ $t('选择要变更的服务') }}：</span>
        </div>
        <div class="form-item-right">
          <bk-select :disabled="true" v-model="formData.serviceSelected">
            <bk-option
              v-for="item in serviceList"
              :key="item.id"
              :id="item.id"
              :name="item.name">
            </bk-option>
          </bk-select>
        </div>
      </div>

      <div class="form-item">
        <div class="form-item-left">
          <span>{{ $t('插件类型') }}：</span>
        </div>
        <div class="form-item-right">
          <bk-select v-model="formData.pluginType" :clearable="false" @selected="changePluginType">
            <bk-option v-for="item in pluginTypeList" :key="item.id" :id="item.id" :name="item.name">
            </bk-option>
          </bk-select>
        </div>
      </div>

      <div class="form-item">
        <div class="form-item-left">
          <span>{{ isUpdate ? $t('选择要更新的插件') : $t('选择插件') }}：</span>
        </div>
        <div class="form-item-right">
          <bk-select
            v-model="formData.pluginName"
            searchable
            :clearable="false"
            :loading="loadingPlugin"
            @selected="changePluginName">
            <bk-option
              v-for="item in pluginList"
              :key="item.id"
              :id="item.name"
              :name="item.name"
              :disabled="item.disabled">
            </bk-option>
          </bk-select>
          <div class="bk-right-info" v-if="formData.pluginName">
            <span class="bk-info-icon">!</span>
            <span>
              <span style="margin-right: 14px">{{ formData.pluginName }}</span>{{ formData.pluginDetail }}
            </span>
          </div>
        </div>
      </div>

      <div class="form-item" v-if="isUpdate">
        <div class="form-item-left">
          <span>{{ $t('选择新包') }}：</span>
        </div>
        <div class="form-item-right">
          <bk-select
            v-model="formData.newPackage"
            :clearable="false"
            :loading="loadingPackage"
            :disabled="!formData.pluginName"
            @selected="changePackage">
            <bk-option
              v-for="item in newPackageList"
              :key="item.id"
              :id="item.id"
              :name="item.name">
            </bk-option>
          </bk-select>
          <div class="bk-right-info" v-if="formData.newPackage !== ''">
            <span class="bk-info-icon">!</span>
            <span>
              <span>
                M D 5 {{ $t('值') }}:<span style="margin-left: 10px">{{ packages.md5 }}</span>
              </span>
              <br />
              <span>
                <!-- eslint-disable-next-line vue/no-v-html -->
                {{ $t('更新时间') }}:<span style="margin-left: 10px" v-html="packages.pkg_mtime"></span>
              </span>
            </span>
          </div>
          <div class="bk-right-checkbox">
            <form class="bk-form">
              <div class="bk-form-item">
                <div
                  class="bk-form-content"
                  style="margin-left: 0px;"
                  v-for="(node, index) in packageCheckList"
                  :key="index">
                  <label
                    :class="['bk-form-checkbox', { 'is-checked': formData[node.key] }]"
                    @click="checkPackage(node, index)">
                    <span class="bk-checkbox"></span>
                    <input type="hidden" name="checkPackage" :checked="formData[node.key]">
                    <span class="bk-checkbox-text">{{ node.name }}</span>
                  </label>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
    <div class="bk-process-btn mt30">
      <bk-button theme="default" @click="stepHandle(1)" :disabled="loadingConfirm">
        {{ $t('上一步') }}
      </bk-button>
      <span style="margin-left: 20px"></span>
      <bk-button theme="primary" @click="clickNext" :loading="loadingConfirm">
        {{ $t('立即执行') }}
      </bk-button>
    </div>
  </section>
</template>

<script>
// import Tips from '@/components/common/tips.vue'
import { PluginOldStore } from '@/store/index';
export default {
  props: {
    ipInfo: {
      type: Object,
      default() {
        return {
          os_type: '',
          bk_biz_id: [],
          conditions: [],
          isAllChecked: false,
          exclude_hosts: [],
          bk_host_id: [],
          name: '',
          keep_config: false,
          no_restart: false,
          version: '',
          job_type: 'MAIN_INSTALL_PLUGIN',
          plugin_type: 'official',
        };
      },
      validator(info) {
        return info ? info.os_type : false;
      },
    },
  },
  data() {
    return {
      initVersion: !!this.ipInfo.name && !!this.ipInfo.version,
      loadingConfirm: false,
      loadingPlugin: false,
      loadingPackage: false,
      operateList: [
        { id: 'MAIN_INSTALL_PLUGIN', name: window.i18n.t('插件更新') },
        { id: 'MAIN_START_PLUGIN', name: window.i18n.t('启动') },
        { id: 'MAIN_STOP_PLUGIN', name: window.i18n.t('停止') },
        { id: 'MAIN_RESTART_PLUGIN', name: window.i18n.t('重启') },
        { id: 'MAIN_RELOAD_PLUGIN', name: window.i18n.t('重载') },
        { id: 'MAIN_DELEGATE_PLUGIN', name: window.i18n.t('托管') },
        { id: 'MAIN_UNDELEGATE_PLUGIN', name: window.i18n.t('取消托管') },
      ],
      serviceList: [
        { id: 1, name: `GSE ${this.$t('插件')}` },
      ],
      pluginTypeList: [
        { id: 'official', name: window.i18n.t('官方插件') },
        { id: 'external', name: window.i18n.t('第三方插件') },
        { id: 'scripts', name: window.i18n.t('脚本插件') },
      ],
      pluginList: [],
      plugin: {}, // 插件信息
      packageCheckList: [
        { key: 'keepConfig', name: this.$t('保留原有配置文件') },
        { key: 'noRestart', name: this.$t('仅更新文件，不重启进程') },
      ],
      newPackageList: [],
      packages: {}, // 插件包信息
      formData: {
        jobType: this.ipInfo.job_type,
        serviceSelected: 1,
        pluginType: this.ipInfo.plugin_type,
        pluginName: this.ipInfo.name,
        pluginDetail: '',
        newPackage: '',
        keepConfig: !!this.ipInfo.keep_config,
        noRestart: !!this.ipInfo.no_restart,
      },
    };
  },
  computed: {
    isUpdate() {
      return this.formData.jobType === 'MAIN_INSTALL_PLUGIN';
    },
  },
  created() {
    this.initPluginSelected();
  },
  methods: {
    // 获取插件分类
    initPluginSelected() {
      if (this.pluginTypeList.length) {
        const value = this.ipInfo.plugin_type || this.pluginTypeList[0].id;
        this.getPluginList(value);
      }
    },
    // 按分类获取插件列表
    async getPluginList(value) {
      this.loadingPlugin = true;
      const data = await PluginOldStore.getProcessList(value);
      this.loadingPlugin = false;
      this.pluginList = data;
      if (data.length) {
        const defaultName = this.formData.pluginName;
        const firstItem = defaultName && data.find(item => item.name === defaultName) ? { name: defaultName } : data[0];
        this.changePluginName(firstItem.name);
      } else {
        this.changePluginName('');
      }
    },
    // 按插件获取包
    async getPackageList(value) {
      this.loadingPackage = true;
      const data = await PluginOldStore.listPackage({
        pk: value,
        data: {
          os: this.ipInfo.os_type,
        },
      });
      this.newPackageList = data;
      this.newPackageList.forEach((item) => {
        item.name = item.pkg_name;
      });
      if (data.length && this.initVersion) {
        this.initVersion = false;
        const curPackage = data.find(item => item.version === this.ipInfo.version);
        if (curPackage) {
          this.formData.newPackage = curPackage.id;
          this.packages = curPackage;
        }
      } else {
        this.packages = {};
      }
      this.loadingPackage = false;
    },
    clearInfo() {
      Object.assign(this.formData, {
        pluginName: '',
        pluginDetail: '',
        newPackage: '',
        noRestart: false,
        keepConfig: false,
      });
      this.packages = {};
    },
    changeOperation(item) {
      if (item.id !== this.formData.jobType) {
        const oldType = this.formData.jobType;
        this.formData.jobType = item.id;
        if (oldType === 'MAIN_INSTALL_PLUGIN') {
          this.clearInfo();
        }
        if (item.id === 'MAIN_INSTALL_PLUGIN') {
          this.newPackageList = [];
          this.clearInfo();
        }
      }
    },
    // 插件类型
    changePluginType(value) {
      // 清空插件信息
      this.plugin = {};
      this.packages = {};
      this.formData.pluginName = '';
      this.formData.newPackage = '';
      this.newPackageList = [];
      this.getPluginList(value);
    },
    // 选择插件
    changePluginName(val) {
      this.formData.pluginName = val;
      const item = this.pluginList.find(item => item.name === val);
      if (val && item) {
        this.formData.pluginName = val;
        this.formData.pluginDetail = this.$i18n.locale === 'en' ? item.scenario_en : item.scenario;
        // 插件信息
        this.plugin = item;

        if (this.isUpdate) {
          // 重置新包选项
          this.formData.newPackage = '';
          this.packages = {};
          this.newPackageList = [];

          const value = item.name;
          this.getPackageList(value);
        }
      } else {
        this.formData.pluginName = '';
        this.formData.pluginDetail = '';
        this.formData.newPackage = '';
      }
    },
    // 选择新包
    changePackage(id) {
      const data = this.newPackageList.find(item => item.id === id);
      this.packages = data || {};
    },
    // 选择包文件配置
    checkPackage(node) {
      this.formData[node.key] = !this.formData[node.key];
    },
    getParams() {
      const params = {
        job_type: this.formData.jobType,
        bk_biz_id: this.ipInfo.bk_biz_id,
      };
      const pluginParams = {
        name: this.formData.pluginName,
      };
      if (this.isUpdate) {
        pluginParams.version = this.packages.version;
        pluginParams.keep_config = this.formData.keepConfig ? 1 : 0;
        pluginParams.no_restart = this.formData.noRestart ? 1 : 0;
      }
      // params.plugin_params = pluginParams // 1.x版本使用的参数
      params.plugin_params_list = [pluginParams]; // 2.x版本使用的参数

      if (this.ipInfo.isAllChecked) {
        params.conditions = this.ipInfo.conditions;
        params.exclude_hosts = this.ipInfo.exclude_hosts;
      } else {
        const bkHostId = this.ipInfo.bk_host_id;
        params.bk_host_id = Array.isArray(bkHostId) ? bkHostId : [bkHostId];
      }
      return params;
    },
    // 提交
    async handleConfirm() {
      if (!this.loadingConfirm) {
        this.loadingConfirm = true;
        const params = this.getParams();
        const data = await PluginOldStore.operatePlugin(params);
        if (data ? data.job_id : false) {
          this.$router.push({ name: 'taskDetail', params: { taskId: data.job_id } });
        }
        this.loadingConfirm = false;
      }
    },
    // 立即执行
    clickNext() {
      const checkedRes = this.isUpdate ? !this.checkPlugInfo() : !this.checkProcessInfo();
      if (checkedRes) {
        this.handleConfirm();
      }
    },
    // 参数校验
    checkProcessInfo() {
      let msg = this.$t('请选择操作');
      msg = this.formData.jobType && this.plugin.id ? '' : this.$t('请选择插件');
      if (msg) {
        this.$bkMessage({
          message: msg,
          theme: 'error',
        });
      }
      return !!msg;
    },
    // 参数校验
    checkPlugInfo() {
      let msg = '';
      if (this.formData.jobType && this.plugin.id) {
        if (this.formData.newPackage === '') {
          msg = this.$t('请选择新包');
        }
      } else {
        msg = this.$t('请选择插件');
      }
      if (msg) {
        this.$bkMessage({
          message: msg,
          theme: 'error',
        });
      }
      return !!msg;
    },
    stepHandle(step) {
      this.$emit('stepChange', step);
    },
  },
};
</script>
<style lang="postcss" scoped>
  .bk-form-checkbox {
    font-size: 14px;
    color: #666;
    margin-right: 30px;
    line-height: 18px;
    display: inline-block;
    padding: 7px 0;
  }
  .bk-form-checkbox.bk-checkbox-small input[type=checkbox] {
    width: 14px;
    height: 14px;
    background-position: 0 -95px;
  }
  .bk-plugin-operation {
    position: relative;
  }
  .operat-container {
    width: 736px;
    margin: 90px auto 0;
    .form-item {
      display: flex;
      margin-bottom: 20px;
      width: 100%;
    }
    .form-item-left {
      padding-right: 10px;
      width: 140px;
      line-height: 32px;
      text-align: right;
      font-size: 14px;
      color: #737987;
    }
    .form-item-right {
      flex: 1;
    }
    .btn-item {
      width: 120px;
      >>> span {
        width: 88px;
        display: inline-block;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }
      &:nth-child(n + 6) {
        margin-top: 4px;
      }
    }
    .bk-right-info {
      position: relative;
      margin-top: 30px;
      padding: 10px 10px 10px 38px;
      width: 100%;
      line-height: 32px;
      font-size: 14px;
      background-color: #ebf4ff;
      .bk-info-icon {
        position: absolute;
        top: 18px;
        left: 14px;
        width: 16px;
        height: 16px;
        text-align: center;
        line-height: 16px;
        background-color: #737987;
        color: #fff;
        font-size: 12px;
        font-weight: bold;
        border-radius: 50%;
      }
    }
  }
  .plugin-btn {
    width: 120px;
    >>> span {
      width: 88px;
      display: inline-block;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
  }
  .bk-process-btn {
    text-align: center;
    button {
      min-width: 100px;
    }
  }
</style>
