<template>
  <div :class="['task-config-wrapper', { 'permission-disabled': !hasPermission }]" v-bkloading="{ isLoading: loading }">
    <section class="task-config-container" v-if="hasPermission">
      <bk-form class="task-config-form" :label-width="165" :model="configParam" ref="taskConfigForm">
        <div class="bk-form-info-item clearfix">
          <bk-form-item
            class="fl"
            required
            property="installPAgentTimeout"
            error-display-type="normal"
            :label="$t('安装PAgent超时时间')"
            :rules="rules.outTime">
            <bk-input v-model.trim="configParam.installPAgentTimeout" :placeholder="$t('请输入')">
              <template slot="append">
                <div class="group-text">s</div>
              </template>
            </bk-input>
            <bk-popover theme="light" placement="right-start" class="info-tooltips">
              <span class="nodeman-icon nc-tips-fill fl info-tooltips-icon"></span>
              <div class="info-tooltips-content" slot="content">{{ $t('安装PAgent超时时间tip') }}</div>
            </bk-popover>
          </bk-form-item>
        </div>

        <div class="bk-form-info-item clearfix">
          <bk-form-item
            class="fl"
            required
            property="installAgentTimeout"
            error-display-type="normal"
            :label="$t('安装Agent超时时间')"
            :rules="rules.outTime">
            <bk-input v-model.trim="configParam.installAgentTimeout" :placeholder="$t('请输入')">
              <template slot="append">
                <div class="group-text">s</div>
              </template>
            </bk-input>
            <bk-popover theme="light" placement="right-start" class="info-tooltips">
              <span class="nodeman-icon nc-tips-fill fl info-tooltips-icon"></span>
              <div class="info-tooltips-content" slot="content">{{ $t('安装Agent超时时间tip') }}</div>
            </bk-popover>
          </bk-form-item>
        </div>

        <div class="bk-form-info-item clearfix">
          <bk-form-item
            class="fl"
            required
            property="installProxyTimeout"
            error-display-type="normal"
            :label="$t('安装Proxy超时时间')"
            :rules="rules.outTime">
            <bk-input v-model.trim="configParam.installProxyTimeout" :placeholder="$t('请输入')">
              <template slot="append">
                <div class="group-text">s</div>
              </template>
            </bk-input>
            <bk-popover theme="light" placement="right-start" class="info-tooltips">
              <span class="nodeman-icon nc-tips-fill fl info-tooltips-icon"></span>
              <div class="info-tooltips-content" slot="content">{{ $t('安装Proxy超时时间tip') }}</div>
            </bk-popover>
          </bk-form-item>
        </div>

        <div class="bk-form-info-item clearfix">
          <bk-form-item
            class="fl"
            required
            property="installDownloadLimitSpeed"
            error-display-type="normal"
            :label="$t('安装下载限速')"
            :rules="rules.speed">
            <bk-input v-model.trim="configParam.installDownloadLimitSpeed" :placeholder="$t('请输入')">
              <template slot="append">
                <div class="group-text">KB/s</div>
              </template>
            </bk-input>
            <bk-popover theme="light" placement="right-start" class="info-tooltips">
              <span class="nodeman-icon nc-tips-fill fl info-tooltips-icon"></span>
              <div class="info-tooltips-content" slot="content">{{ $t('安装下载限速tip') }}</div>
            </bk-popover>
          </bk-form-item>
        </div>

        <div class="bk-form-info-item clearfix">
          <bk-form-item
            class="fl"
            required
            property="parallelInstallNumber"
            error-display-type="normal"
            :label="$t('并行安装数')"
            :rules="rules.install">
            <bk-input v-model.trim="configParam.parallelInstallNumber" :placeholder="$t('请输入')"></bk-input>
          </bk-form-item>
        </div>
        <div class="bk-form-info-item clearfix">
          <bk-form-item
            class="fl"
            required
            property="nodeManLogLevel"
            error-display-type="normal"
            :label="$t('后台日志记录级别')"
            :rules="rules.must">
            <bk-select v-model="configParam.nodeManLogLevel" ext-cls="log-level-select" :clearable="false">
              <bk-option
                v-for="option in logLevelMap"
                :key="option.id"
                :id="option.id"
                :name="option.name">
              </bk-option>
            </bk-select>
          </bk-form-item>
        </div>

        <div class="bk-form-info-item item-button-group mt30 clearfix">
          <bk-form-item>
            <bk-button
              class="nodeman-primary-btn"
              theme="primary"
              :loading="submitLoading"
              :disabled="submitLoading"
              @click="submitHandler">
              {{ $t('保存') }}
            </bk-button>
            <bk-button
              class="nodeman-cancel-btn"
              theme="default"
              :disabled="submitLoading"
              @click="resetHandler">
              {{ $t('重置') }}
            </bk-button>
          </bk-form-item>
        </div>
      </bk-form>
    </section>
    <exception-page v-else type="notPower" :sub-title="$t('全局任务Auth')" @click="handleApplyPermission"></exception-page>
  </div>
</template>

<script lang="ts">
import { Component, Ref } from 'vue-property-decorator';
import { ConfigStore } from '@/store';
import ExceptionPage from '@/components/exception/exception-page.vue';
import formLabelMixin from '@/common/form-label-mixin';
import { bus } from '@/common/bus';
import { reguFnRangeInteger, reguNaturalNumber, reguRequired } from '@/common/form-check';

@Component({
  name: 'TaskConfig',
  components: {
    ExceptionPage,
  },
})

export default class TaskConfig extends formLabelMixin {
  @Ref('taskConfigForm') private readonly taskConfigForm!: any;

  private loading = false;
  private submitLoading = false;
  private configParam: { [key: string]: any } = {
    installPAgentTimeout: 300,
    installAgentTimeout: 300,
    installProxyTimeout: 300,
    installDownloadLimitSpeed: 0,
    parallelInstallNumber: 100,
    nodeManLogLevel: 'ERROR',
  };
  private defaultsParam: { [key: string]: any } = {};
  private logLevelMap = [
    { id: 'ERROR', name: 'Error' },
    { id: 'INFO', name: 'Error、Info' },
    { id: 'DEBUG', name: 'Error、Info、Debug' },
  ];
  private hasPermission = true;
  private rules = {
    must: [reguRequired],
    speed: [reguRequired, reguNaturalNumber,
    ],
    install: [reguRequired, reguFnRangeInteger(1, 2000)],
    outTime: [reguRequired, reguFnRangeInteger(0, 86400)],
  };

  private created() {
    this.hasPermission = window.PROJECT_CONFIG.GLOBAL_TASK_CONFIG_PERMISSION === 'True';
  }
  private mounted() {
    if (this.hasPermission) {
      Object.assign(this.defaultsParam, this.configParam);
      this.requestConfig();
      this.initLabelWidth(this.taskConfigForm);
    }
  }

  private submitHandler() {
    this.taskConfigForm.validate().then(() => {
      this.saveConfig();
    })
      .catch(() => {});
  }
  private resetHandler() {
    Object.assign(this.configParam, this.defaultsParam);
  }
  private async requestConfig() {
    this.loading = true;
    const res = await ConfigStore.requestGlobalSettings();
    Object.assign(this.configParam, res.jobSettings);
    this.loading = false;
  }
  private async saveConfig() {
    this.submitLoading = true;
    const {
      installPAgentTimeout, installAgentTimeout, installProxyTimeout,
      installDownloadLimitSpeed, parallelInstallNumber, nodeManLogLevel,
    } = this.configParam;
    const res = await ConfigStore.saveGlobalSettings({
      install_p_agent_timeout: installPAgentTimeout,
      install_agent_timeout: installAgentTimeout,
      install_proxy_timeout: installProxyTimeout,
      install_download_limit_speed: installDownloadLimitSpeed,
      parallel_install_number: parallelInstallNumber,
      node_man_log_level: nodeManLogLevel,
    });
    if (res.result) {
      this.$bkMessage({
        theme: 'success',
        message: this.$t('保存配置成功'),
      });
    }
    this.submitLoading = false;
  }
  private handleApplyPermission() {
    bus.$emit('show-permission-modal', {
      params: { apply_info: [{ action: 'globe_task_config' }] },
    });
  }
}
</script>

<style lang="postcss" scoped>
  .task-config-wrapper {
    min-height: calc(100vh - 142px);
    &.permission-disabled {
      display: flex;
    }
    .task-config-container {
      margin-top: 24px;
      display: flex; /** 为了处理form验证后自定义tooltip不生效问题 */
      padding-bottom: 40px;
    }
    .task-config-form {
      width: 525px;
    }
    >>> .bk-form-control {
      width: 315px;
    }
    .bk-form-info-item {
      font-size: 0;
      .group-text {
        padding: 0;
        width: 31px;
        text-align: center;
      }
    }
    .bk-form-info-item + .bk-form-info-item {
      margin-top: 20px;
    }
    .info-tooltips {
      position: absolute;
      top: 0;
      left: 100%;
      height: 100%;
    }
    .info-tooltips-icon {
      margin: 7px 0 0 10px;
      font-size: 16px;
      color: #c4c6cc;
    }
    .log-level-select {
      width: 315px;
      background: #fff;
    }
  }
  .info-tooltips-content {
    max-width: 370px;
    color: #63656e;
  }
</style>
