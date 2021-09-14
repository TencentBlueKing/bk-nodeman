<template>
  <div class="rule-create" v-test.policy="'policyProcess'">
    <div :class="[isPolicyOperate ? '' : 'header']">
      <div class="nodeman-navigation-content">
        <span class="content-icon">
          <i class="nodeman-icon nc-back-left" @click="routerBack"></i>
        </span>
        <span class="content-header">{{ navTitle }}</span>
        <span class="content-subtitle" v-if="showRemarks">{{ titleRemarks }}</span>
      </div>
      <template v-if="!previewOperate">
        <bk-steps v-if="isPluginRule" :steps="steps" :cur-step.sync="curStep"></bk-steps>
        <RuleStep
          v-test.policy="'policyStep'"
          v-else
          :steps="steps"
          :controllable="createOperate ? false : hasSelectedTarget"
          :show-tips="createOperate && !loading"
          :value="curStep"
          @change="handleStepChange">
          <template v-if="!createOperate && !hasSelectedTarget" slot="disable-tips">
            {{ $t('至少选择一个目标') }}
          </template>
        </RuleStep>
      </template>
    </div>
    <div
      :class="['content', previewOperate ? 'pt20' : (componentName !== 'paramsConfig' ? 'pt30' : '')]"
      v-bkloading="{ isLoading: loading }">
      <!-- <keep-alive> -->
      <template v-if="!loading">
        <component
          class="rule-component"
          v-for="step in steps"
          :key="step.com"
          :ref="`${step.com}Ref`"
          :is="components[step.com]"
          :type="type"
          :rule-id="id"
          :plugin-name="pluginName"
          :abnormal-host="bkHostId"
          :step="step.icon"
          :step-loading="stepLoading"
          :invisible-step="invisibleStep"
          :has-pre-step="curStep > 1 && !previewOperate"
          v-show="componentName === step.com"
          @update-loaded="handleUpdateStepLoaded"
          @update-reload="handleUpdateStepReload"
          @step-change="handleStepChange"
          @cancel="handleCancel">
        </component>
      </template>
      <!-- </keep-alive> -->
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { PluginStore } from '@/store';
import { stepMap, titleMap } from './pluginConfig';
import routerBackMixin from '@/common/router-back-mixin';
import DeployTarget from './deploy-target.vue';
import DeployVersion from './deploy-version.vue';
import ParamsConfig from './params-config.vue';
import PerformPreview from './perform-preview.vue';
import RuleStep from './rule-step.vue';
import { TranslateResult } from 'vue-i18n';
import { pluginOperate, previewOperate, policyOperateType, stepOperate } from '@/views/plugin/operateConfig';
import { IStep, IStrategy } from '@/types/plugin/plugin-type';

const formatStepMap: { [key: string]: IStep[] } = {};
Object.keys(stepMap).forEach((key) => {
  formatStepMap[key] = stepMap[key].map(item => ({
    ...item,
    disabled: false,
    error: false,
  }));
});

@Component({
  name: 'create-rule',
  components: {
    RuleStep,
  },
})
export default class CreateRule extends Mixins(routerBackMixin) {
  // 策略相关的操作 & 手动 安装/更新 插件会进入此流程路由
  @Prop({ default: 'create', type: String, required: true }) private readonly type!: string;

  @Prop({ default: '', type: [String, Number] })private readonly pluginId!: number | string;
  @Prop({ default: '', type: String })private readonly pluginName!: string;
  @Prop({ default: '', type: [String, Number] })private readonly policyName!: number | string;
  @Prop({ default: 0, type: [String, Number] }) private readonly id!: number | string;
  @Prop({ default: 0, type: [String, Number] }) private readonly subId!: number | string; // 灰度策略id - 仅 发布 用到
  @Prop({ default: () => [], type: Array }) private readonly bkHostId!: number | string; // 失败重试带的主机id

  private loading = false;
  private stepLoading = false;
  private curStep = 1;
  private components = {
    deployTarget: DeployTarget,
    deployVersion: DeployVersion,
    paramsConfig: ParamsConfig,
    performPreview: PerformPreview,
  };
  private stepMap = formatStepMap;
  private title: TranslateResult = '';
  private titleRemarks = '';
  // 导致不可预览的步骤
  private invisibleStep = -1;
  // 已加载的步骤
  private stepLoadedMap: Dictionary = {
    step1: false,
    step2: false,
    step3: false,
    step4: false,
  };
  // 需要重载的步骤
  private stepReloadMap: Dictionary = {
    step1: false,
    step2: false,
    step3: false,
    step4: false,
  };

  private get createOperate() {
    return ['create', 'createGray'].includes(this.type);
  }
  // 只有预览的操作类型
  private get previewOperate() {
    return previewOperate.includes(this.type);
  }
  private get isPolicyOperate() {
    return policyOperateType.includes(this.type);
  }
  private get isPluginRule() {
    return PluginStore.isPluginRule;
  }
  private get showRemarks() {
    return (this.previewOperate && !['deleteGray', 'releaseGray'].includes(this.type))
      || stepOperate.includes(this.type)
      || /edit/.test(this.type);
  }
  private get steps() {
    return this.stepMap[this.type] || [];
  }

  private get componentName() {
    return this.steps[this.curStep - 1] ? this.steps[this.curStep - 1].com : 'performPreview';
  }
  private get navTitle() {
    return this.title || this.$route.params.title || this.$route.meta.title;
  }
  private get hasSelectedTarget() {
    return !!PluginStore.strategyData.scope?.nodes.length;
  }
  // 方便观察store数据
  private get strategyData() {
    return PluginStore.strategyData;
  }

  private created() {
    PluginStore.setStrategyData();
    PluginStore.updateOperateType(this.type);
    PluginStore.updateBizRange();
    PluginStore.updateScopeRange(null);

    this.title = titleMap[this.type];
    let titleRemarks = `(${this.pluginName}`;
    titleRemarks += this.policyName ? ` - ${this.policyName})` : ')';
    if (this.type === 'create') {
      // deploy-version、upgrade-version 插件包版本相关接口需要这两值
      PluginStore.setStateOfStrategy({
        key: 'plugin_info',
        value: {
          id: this.pluginId,
          name: this.pluginName,
        },
      });
    // 手动操作插件类型 - 跳过选择目标步骤， 直接模拟好策略相关的数据
    } else if (pluginOperate.includes(this.type)) {
      PluginStore.setStrategyData(this.$route.params.strategyData as unknown as IStrategy);
    } else if (['createGray', 'editGray', 'releaseGray'].includes(this.type)) {
      this.getGrayRuleInfo();
    } else {
      this.getPolicyInfo();
    }
    this.titleRemarks = titleRemarks;
  }

  /**
   * 新建策略只能按顺序进行步骤切换, 编辑策略可随意切换步骤(存在选中目标)
   *
   * 第一步 - 策略目标 若未选中目标，禁止后续操作, 目标变动之后会影响第二步的 操作系统+插件版本选项数量
   * 第二步 - 策略版本 始终不会有未完成提示, 调用插件版本接口后始终会有默认值
   * 第三步 - 策略参数 第二步变动之后可能出现未填的必填参数 // 目前阶段没有参数
   * 第四步 - 策略预览 若策略目标变动过(第一步)。检查第三步是否存在未未填的必填参数
   *
   * 策略目标(第一步)变动后需要重新调用第二步的初始化。若第二部变动，则需要再调用第三步的初始化
   * configs(策略版本)、params(策略参数) 数据多增少删、已有替换
   */
  public async handleStepChange(step: number) {
    const oldStepIcon = this.curStep;
    // 目标步骤
    const toStepItem = this.steps.find(item => item.icon === step) as IStep;
    const toStepRef = this.getStepRef(toStepItem.com);
    if (this.curStep > step) {
      this.curStep = step;
      const toStepStr = `step${step}`;
      if (!this.stepLoadedMap[toStepStr] || this.stepReloadMap[toStepStr]) {
        toStepRef.initStep && toStepRef.initStep();
      }
    } else {
      let hasStepChanged = false;
      // 上一步是否变更
      let nextChanged = false;
      let stepIndex = this.curStep - 1;
      const targetStepIndex = step - 1;
      const changedStep: number[] = []; // 改动过的步骤
      const checkFailedStep: number[] = []; // 校验不同过的步骤 - 仅参数配置步骤可能会出现必填项为空的情况(第二或第三步)
      this.curStep = step;
      // 重载、验证 跳过的步骤 (策略版本、参数配置)
      if (stepIndex < targetStepIndex) {
        this.stepLoading = true;
        while (stepIndex < targetStepIndex) {
          const stepIcon = stepIndex + 1;
          const curStepRef = this.getStepRef(this.steps[stepIndex].com);
          let changed = false;
          let checkFailed = false;
          // 如果上一步变更过
          if (nextChanged || this.stepReloadMap[`step${stepIndex}`]) {
            if (curStepRef.initStep) {
              await curStepRef.initStep();
            }
          }
          if (nextChanged || this.stepReloadMap[`step${stepIcon}`] || stepIcon === oldStepIcon) {
            if (curStepRef.beforeStepLeave) {
              changed = await curStepRef.beforeStepLeave();
              if (changed) {
                changedStep.push(stepIndex);
              }
            }
            if (curStepRef.handleValidateForm) {
              checkFailed = await curStepRef.handleValidateForm();
              // console.log(checkFailedStep, checkFailed, 'checkFailed')
              if (checkFailed) {
                checkFailedStep.push(stepIcon);
              }
            }
          }
          nextChanged = changed;
          stepIndex += 1;
        }
        hasStepChanged = !!changedStep.length;
        this.stepLoading = false;
      }
      this.steps.forEach((stepItem) => {
        stepItem.error = checkFailedStep.includes(stepItem.icon);
      });
      this.invisibleStep = checkFailedStep[0] || -1;
      this.$nextTick(() => {
        // 当前
        const stepKey = `step${step}`;
        // console.log(stepKey, nextChanged, hasStepChanged, !this.stepLoadedMap[stepKey], this.stepReloadMap[stepKey])
        if (nextChanged || hasStepChanged || !this.stepLoadedMap[stepKey] || this.stepReloadMap[stepKey]) {
          toStepRef.initStep && toStepRef.initStep();
        }
      });
    }
  }
  // 更新需要初始化的步骤
  public handleUpdateStepLoaded({ step, loaded }: { step: number, loaded?: boolean }) {
    this.stepLoadedMap[`step${step}`] = loaded;
    this.stepReloadMap[`step${step}`] = false;
  }
  // 更新需要重新初始化的步骤
  public handleUpdateStepReload({ step, needReload }: { step: number, needReload?: boolean }) {
    this.stepReloadMap[`step${step}`] = !!needReload;
    if (needReload) {
      const lastStep = this.steps[this.steps.length - 1];
      const lastIcon = lastStep.icon;
      this.stepReloadMap[`step${lastIcon}`] = !!needReload;
    }
  }
  // 获取指定步骤的ref
  public getStepRef(stepCom: string): any {
    const stepRefs: any = this.$refs[`${stepCom}Ref`];
    return stepRefs.length ? stepRefs[0] : stepRefs;
  }

  public handleCancel() {
    PluginStore.setStrategyData();
    const { parentName = 'pluginRule' } = this.$route.meta;
    this.$router.push({ name: parentName });
  }

  public async getPolicyInfo() {
    this.loading = true;
    const res = await PluginStore.getPolicyInfo(this.id);
    PluginStore.setStrategyData(res);
    if (/edit/.test(this.type)) {
      this.titleRemarks = `(${this.strategyData.name as string})`;
    }
    this.loading = false;
  }
  // 灰度策略 新增、编辑、发布初始化(主策略和灰度策略加载顺序不一样)
  public async getGrayRuleInfo() {
    this.loading = true;
    let policyRes: any = { configs: [], params: [] };
    let grayRes: any = { configs: [], params: [] };
    if ('releaseGray' === this.type) {
      policyRes = await PluginStore.getPolicyInfo(this.id);
      grayRes = await PluginStore.getPolicyInfo(this.subId);

      // 发布 - 将灰度策略的版本和参数替换给主策略
      this.replacePolicyValue(grayRes.configs, policyRes.configs, 'os', 'cpu_arch');
      this.replacePolicyValue(grayRes.params, policyRes.params, 'os_type', 'cpu_arch');

      PluginStore.setStrategyData(policyRes);
    } else if (['createGray', 'editGray'].includes(this.type)) {
      if ('editGray' === this.type) {
        grayRes = await PluginStore.getPolicyInfo(this.id);
        PluginStore.setStrategyData(grayRes);
      } else {
        PluginStore.setStateOfStrategy({ key: 'plugin_info', value: { id: this.pluginId, name: this.pluginName } });
      }
      if (grayRes.pid > -1 || 'createGray' === this.type) {
        // 限制灰度策略仅能够选主策略包含业务下的主机
        policyRes = await PluginStore.getPolicyInfo(grayRes.pid > -1 ? grayRes.pid : this.id);
        PluginStore.updateBizRange((policyRes.bk_biz_scope || []));
        PluginStore.updateScopeRange(policyRes.scope);
      }
    }
    this.loading = false;
  }
  public replacePolicyValue(targetList: any[], sourceList: any[], os: string, arch: string) {
    targetList.forEach((item) => {
      const index = sourceList.findIndex(config => `${config[os]} ${config[arch]}` === `${item[os]} ${item[arch]}`);
      if (index > -1) {
        sourceList.splice(index, 1, item);
      } else {
        sourceList.push(item);
      }
    });
  }
}
</script>
<style lang="postcss" scoped>
$bgColor: #f5f7fa;

.header {
  background: $bgColor;
}
>>> .bk-steps {
  padding: 0 16% 20px 16%;
  border-bottom: 1px solid #f0f1f5;
}
>>> .bk-step {
  .bk-step-number {
    border: 1px solid #979ba5;
    color: #979ba5;
  }
  .bk-step-title {
    color: #63656e;
  }
  &.done {
    .bk-step-number {
      border-color: #c4c6cc;
      color: #fff;
      background: #c4c6cc;
    }
    .bk-step-title {
      color: #313238;
    }
  }
  &.current {
    .bk-step-title {
      color: #313238;
    }
  }
}
.nodeman-navigation-content {
  line-height: 20px;
  display: flex;
  align-items: center;
  padding: 20px 24px;
  .content-icon {
    position: relative;
    height: 20px;
    top: -4px;
    margin-left: -7px;
    font-size: 28px;
    color: #3a84ff;
    cursor: pointer;
  }
  .content-header {
    font-size: 16px;
    color: #313238;
  }
  .content-subtitle {
    margin-left: 8px;
    font-size: 12px;
    color: #979ba5;
  }
}
.rule-create {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 52px);
  overflow: hidden;
  .content {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: auto;
    background: #fff;
    .rule-component {
      flex: 1;
    }
  }
}
</style>
