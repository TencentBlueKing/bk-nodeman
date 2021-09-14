<template>
  <bk-form v-test.policy="'versionForm'" class="align-form" ref="form" v-bkloading="{ isLoading: loading }">
    <bk-form-item v-if="showTips">
      <Tips
        :list="$t('通过检测现有主机操作系统已自动选中必须部署的插件包')"
        class="mb20 version-tips">
      </Tips>
    </bk-form-item>
    <bk-form-item
      :label="labelText"
      required>
      <div class="table-status" v-if="showTips">
        <i18n path="已选择部署版本个数">
          <span class="num">{{ selectedVersion.length }}</span>
        </i18n>
      </div>
      <DeployVersionTable
        class="version-table"
        :plugin-id="pluginId"
        :data="pluginConfig"
        :show-select="showTips"
        :selected="selectedVersion"
        @checked="handleSelected"
        @version-change="handleUpdateReload({ step: step + 1, needReload: true })">
      </DeployVersionTable>
    </bk-form-item>
    <bk-form-item>
      <bk-button
        v-test.common="'stepNext'"
        theme="primary"
        class="nodeman-primary-btn"
        :disabled="!selectedVersion.length"
        @click="handleStepChange(step + 1)">
        {{ $t('下一步') }}
      </bk-button>
      <bk-button
        v-if="hasPreStep"
        v-test.common="'stepPrev'"
        class="nodeman-cancel-btn ml5"
        @click="handleStepChange(step - 1)">
        {{ $t('上一步') }}
      </bk-button>
      <bk-button
        class="nodeman-cancel-btn ml5"
        @click="handleCancel">
        {{ $t('取消') }}
      </bk-button>
    </bk-form-item>
  </bk-form>
</template>
<script lang="ts">
import { Component, Mixins, Prop, Ref, Emit } from 'vue-property-decorator';
import { PluginStore } from '@/store';
import DeployVersionTable from './deploy-version-table.vue';
import Tips from '@/components/common/tips.vue';
import FormLabelMixin from '@/common/form-label-mixin';
import { IPk } from '@/types/plugin/plugin-type';
import { deepClone } from '@/common/util';

interface IDeployPk extends IPk {
  'is_preselection': boolean
  disabled?: boolean
  selection?: boolean
}

@Component({
  name: 'deploy-version',
  components: {
    DeployVersionTable,
    Tips,
  },
})
export default class DeployVersion extends Mixins(FormLabelMixin) {
  @Prop({ type: String, default: '' }) private readonly type!: string;
  @Prop({ type: Boolean, default: false }) private readonly hasPreStep!: boolean;
  @Prop({ type: Number, default: 2 }) private readonly step!: number;
  @Ref('form') private readonly form!: any;

  private loading = true;
  private pluginConfig: IPk[] = [];
  private oldSelectedVersion: IPk[] = [];
  // 目标变更后需要重新获取版本详情信息
  // private scopeNodesChange = true

  // @Watch('$store.state.pluginNew.strategyData.scope.nodes')
  // private handleScopeNodesChange() {
  //   this.scopeNodesChange = true
  // }

  private get selectedVersion() {
    return PluginStore.strategyData.configs || [];
  }
  private get selectedVersionMap() {
    return this.selectedVersion.map(item => `${item.os} ${item.cpu_arch} ${item.version}`);
  }
  private get oldSelectedVersionMap() {
    return this.oldSelectedVersion.map(item => `${item.os} ${item.cpu_arch} ${item.version}`);
  }
  private get pluginId() {
    return PluginStore.strategyData.plugin_info?.id;
  }
  private get isGrayRule() {
    return PluginStore.isGrayRule;
  }
  // 手动操作插件
  private get isManualType() {
    return ['MAIN_INSTALL_PLUGIN'].includes(this.type);
  }
  private get showTips() {
    return !this.isGrayRule && !this.isManualType;
  }
  private get labelText() {
    if (this.isGrayRule) {
      return this.$t('灰度版本');
    }
    return this.isManualType ? this.$t('插件版本') : this.$t('部署版本');
  }

  private mounted() {
    this.minWidth = 86;
    this.initLabelWidth(this.form);
    this.cloneSelected();
    if (this.step === 1) {
      this.initStep();
    }
  }
  @Emit('step-change')
  public handleStepChange(step: number) {
    return step;
  }
  @Emit('cancel')
  public handleCancel() {}
  @Emit('update-reload')
  public handleUpdateReload({ step, needReload }: { step: number, needReload?: boolean }) {
    return { step, needReload };
  }
  @Emit('update-loaded')
  public handleUpdateStepLoaded({ step, loaded }: { step: number, loaded?: boolean }) {
    return { step, loaded };
  }

  public handleSelected(selection: IPk[]) {
    PluginStore.setStateOfStrategy({ key: 'configs', value: selection });
  }
  public async initStep() {
    this.loading = true;
    const res = await PluginStore.pluginSelectionDetail({
      plugin_id: PluginStore.strategyData.plugin_info?.id,
      scope: PluginStore.strategyData.scope,
    });
    const oldIndex: number[] = [];
    // 找出原本勾选的 操作系统 项
    this.selectedVersion.forEach((old) => {
      const index = res.plugin_packages
        .findIndex((item: IPk) => `${item.os} ${item.cpu_arch}` === `${old.os} ${old.cpu_arch}`);
      if (index > -1) {
        oldIndex.push(index);
        res.plugin_packages.splice(index, 1, {
          ...old,
          is_preselection: !!res.plugin_packages[index].is_preselection,
        });
      }
    });
    res.plugin_packages.forEach((item: IDeployPk, index: number) => {
      item.disabled = true; // 需配合查询必须插件的接口做禁用限制
      item.support_os_cpu = `${item.os} ${item.cpu_arch}`;
      item.selection = oldIndex.includes(index) || !!item.is_preselection; // 不可取消的选中
    });
    const tableList = this.showTips
      ? res.plugin_packages
      : res.plugin_packages.filter((item: IDeployPk) => !!item.is_preselection);
    this.pluginConfig = tableList;
    this.loading = false;
    this.handleUpdateStepLoaded({ step: this.step, loaded: true });
    return Promise.resolve(tableList);
  }
  public cloneSelected() {
    this.oldSelectedVersion = deepClone(this.selectedVersion);
  }
  // 找出操作选中的操作系统或版本是否变更过 与选中数量无关
  public beforeStepLeave() {
    const selected = this.selectedVersion.map(item => `${item.os} ${item.cpu_arch} ${item.version}`);
    const copySelected = this.oldSelectedVersion.map(item => `${item.os} ${item.cpu_arch} ${item.version}`);
    const res = selected.every(item => copySelected.includes(item));
    if (res) {
      // 仅删除的情况下，删除对应的params
      const params = deepClone(PluginStore.strategyData.params);
      PluginStore.setStateOfStrategy({
        key: 'params',
        value: params.filter((item: Dictionary) => this.selectedVersion
          .find(selected => `${item.os_type} ${item.cpu_arch}` === `${selected.os} ${selected.cpu_arch}`)),
      });
    }
    this.cloneSelected();
    this.handleUpdateReload({ step: this.step + 1, needReload: !res || selected.length !== copySelected.length });
    return !res || selected.length !== copySelected.length;
  }
}
</script>
<style lang="postcss" scoped>
.align-form {
  width: 705px;
}
.table-status {
  padding-left: 16px;
  height: 42px;
  line-height: 42px;
  background: #f0f1f5;
  border: 1px solid #dcdee5;
  border-bottom: 0;
  font-weight: 700;
  .num {
    color: #3a84ff;
  }
}
</style>
