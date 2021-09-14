<template>
  <bk-form v-test.policy="'targetForm'" ref="form" :model="formData" :rules="rules">
    <bk-form-item
      v-if="isCreateType"
      class="rule-name"
      v-test.policy="'name'"
      :label="isGrayRule ? $t('灰度名称') : $t('策略名称')"
      property="policyName"
      required>
      <bk-input :placeholder="$t('请输入策略名称')" v-model.trim="formData.policyName" ref="ruleNameRef"></bk-input>
    </bk-form-item>
    <bk-form-item
      :label="isGrayRule ? $t('灰度目标') : $t('部署目标')"
      class="selector-form"
      required>
      <IpSelect
        class="ip-selector"
        v-test.policy="'ipSelect'"
        :action="['strategy_create', 'strategy_view']"
        :node-type="isGrayRule ? 'INSTANCE' : targetPreview.node_type"
        :checked-data="targetPreview.nodes"
        @check-change="handleTargetChange">
      </IpSelect>
    </bk-form-item>
    <bk-form-item>
      <bk-button
        class="nodeman-primary-btn"
        theme="primary"
        v-test.common="'stepNext'"
        :disabled="!targetPreview.nodes || !targetPreview.nodes.length || !formData.policyName"
        @click="handleNext">
        {{ $t('下一步') }}
      </bk-button>
      <bk-button
        class="nodeman-cancel-btn ml5"
        @click="handleStepCancel">
        {{ $t('取消') }}
      </bk-button>
    </bk-form-item>
  </bk-form>
</template>
<script lang="ts">
import { Mixins, Component, Ref, Emit, Prop } from 'vue-property-decorator';
import FormLabelMixin from '@/common/form-label-mixin';
import IpSelect from '@/components/ip-selector/business/topo-selector-nodeman.vue';
import { PluginStore } from '@/store';
import { ITarget } from '@/types/plugin/plugin-type';
import { reguRequired, reguFnName } from '@/common/form-check';

@Component({
  name: 'deploy-target',
  components: {
    IpSelect,
  },
})
export default class DeployTarget extends Mixins(FormLabelMixin) {
  @Prop({ type: Number, default: 1 }) private readonly step!: number;
  @Ref('form') private readonly form!: any;
  @Ref('ruleNameRef') private readonly ruleNameRef!: any;

  private formData: Dictionary = {
    policyName: PluginStore.strategyData.name || '',
  };
  private rules: Dictionary = {
    policyName: [reguRequired, reguFnName({ max: 40 })],
  };
  private stepChanged = false;

  private get isGrayRule() {
    return PluginStore.isGrayRule;
  }
  private get isCreateType() {
    return PluginStore.isCreateType;
  }
  private get targetPreview() {
    return PluginStore.strategyData.scope || {};
  }

  private mounted() {
    this.minWidth = 86;
    this.initLabelWidth(this.form);
    this.ruleNameRef && this.ruleNameRef.focus();
    if (this.step === 1) {
      this.initStep();
    }
  }

  @Emit('cancel')
  public handleStepCancel() {}
  @Emit('step-change')
  public handleStepChange(step: number) {
    return step;
  }
  @Emit('update-reload')
  public handleUpdateReload({ step, needReload }: { step: number, needReload?: boolean }) {
    return { step, needReload };
  }
  @Emit('update-loaded')
  public handleUpdateStepLoaded({ step, loaded }: { step: number, loaded?: boolean }) {
    return { step, loaded };
  }

  public handleTargetChange({ type, data }: { type: 'INSTANCE' | 'TOPO', data: ITarget[] }) {
    PluginStore.setStateOfStrategy([
      { key: 'scope', value: { object_type: 'HOST', node_type: type, nodes: data } },
    ]);
    this.stepChanged = true;
    // 需要重置 当前步骤为未作改动
    this.handleUpdateReload({ step: this.step + 1, needReload: true });
  }

  public initStep() {
    this.stepChanged = false;
    this.handleUpdateStepLoaded({ step: this.step, loaded: true });
  }
  public async beforeStepLeave() {
    const { stepChanged, formData: { policyName } } = this;
    PluginStore.setStateOfStrategy({ key: 'name', value: policyName });
    this.stepChanged = false;
    return Promise.resolve(!this.targetPreview.nodes.length || stepChanged);
  }
  public async handleNext() {
    const res = await this.form.validate().catch(() => false);
    // if (!this.targetPreview.nodes.length) {
    //   this.$bkMessage({
    //     theme: 'error',
    //     message: this.$t('部署目标必须选择')
    //   })
    //   return
    // }
    if (res) {
      this.handleStepChange(this.step + 1);
    }
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-dialog {
  &-tool {
    min-height: 0;
  }
  &-body {
    padding: 0;
    height: 680px;
  }
}
>>> .rule-name .bk-form-content {
  width: 480px;
}
.selector-form {
  padding-right: 30px;
}
.ip-selector {
  /* stylelint-disable-next-line declaration-no-important */
  height: calc(100vh - 300px) !important;
}
</style>
