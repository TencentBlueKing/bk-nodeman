<template>
  <article class="resource-quota-edit" v-bkloading="{ isLoading: loading }">
    <div class="nodeman-navigation-content mb20">
      <span class="content-icon" @click="handleBack">
        <i class="nodeman-icon nc-back-left"></i>
      </span>
      <span class="content-header">{{ $t('编辑资源配额') }}</span>
      <span class="content-subtitle">{{ moduleName | filterEmpty }}</span>
    </div>
    <section class="page-body">
      <bk-form ref="resource-form" :model="formData">
        <div class="form-head">
          <div class="form-head-item" :style="`width: ${labelWidth + 1}px;`">
            <span>{{ $t('插件名称') }}</span>
          </div>
          <div class="form-head-item">
            <span class="text-underline-dashed" v-bk-tooltips="$t('限制最高CPU使用率')">{{ $t('CPU配额') }}</span>
          </div>
          <div class="form-head-item">
            <span class="text-underline-dashed" v-bk-tooltips="$t('限制最高内存使用率')">{{ $t('内存配额') }}</span>
          </div>
        </div>
        <div class="form-horizontal-item" v-for="item in pluginList" :key="item.plugin_name">
          <bk-form-item
            :property="`${item.plugin_name}_cpu`"
            :label="item.plugin_name"
            :label-width="labelWidth"
            :icon-offset="40"
            :rules="percentRule"
            required>
            <bk-input v-model="formData[`${item.plugin_name}_cpu`]" :placeholder="$t('请输入')">
              <div class="group-text" slot="append">%</div>
            </bk-input>
          </bk-form-item>
          <bk-form-item
            :property="`${item.plugin_name}_mem`"
            :label-width="16"
            :icon-offset="40"
            :rules="percentRule">
            <bk-input v-model="formData[`${item.plugin_name}_mem`]" :placeholder="$t('请输入')">
              <div class="group-text" slot="append">%</div>
            </bk-input>
          </bk-form-item>
        </div>
        <bk-form-item :label-width="labelWidth" class="form-btn-group">
          <bk-button class="action-btn" theme="primary" :loading="submitLoading" @click="handleFormSubmit">
            {{ $t('执行') }}
          </bk-button>
          <bk-button class="action-btn" :disabled="submitLoading" theme="default" @click="handleFormReset">
            {{ $t('还原默认') }}
          </bk-button>
          <bk-button theme="default" :disabled="submitLoading" @click="handleBack">
            {{ $t('取消') }}
          </bk-button>
        </bk-form-item>
      </bk-form>
    </section>
  </article>
</template>
<script lang="ts">
import { Component, Prop, Ref, Vue } from 'vue-property-decorator';
import { reguFnRangeInteger, reguRequired } from '@/common/form-check';
import { PluginStore } from '@/store/index';

@Component({ name: 'resource-quota-edit' })
export default class ResourceQuotaEdit extends Vue {
  @Prop({ type: Number, default: null }) private readonly bizId!: number;
  @Prop({ type: Number, default: null }) private readonly moduleId!: number;

  @Ref('resource-form') private readonly resourceForm!: any;

  public loading = false;
  public submitLoading = false;
  public moduleName = '';
  public labelWidth = 140;
  public formData: any = {};
  public pluginList: any[] = [];
  public percentRule = [
    reguRequired,
    reguFnRangeInteger(0, 100),
  ];

  private created() {
    this.getPluginsConfig();
  }

  public async getPluginsConfig() {
    this.loading = true;
    this.getTemplatesByBiz();
    const res = await PluginStore.fetchResourcePolicy({
      bk_biz_id: this.bizId,
      bk_obj_id: 'service_template',
      bk_inst_id: this.moduleId,
    });
    this.pluginList = res.resource_policy;
    this.handleFormReset();
    this.loading = false;
  }
  public async getTemplatesByBiz() {
    const templates: any[] = await PluginStore.getTemplatesByBiz({ bk_biz_id: this.bizId });
    const curTemp = templates.find(item => item.bk_inst_id === this.moduleId);
    if (curTemp) {
      this.moduleName = curTemp ? `(${curTemp.bk_inst_name})` : '';
    } else {
      this.handleBack();
    }
  }

  public handleFormSubmit() {
    this.resourceForm.validate().then(async () => {
      this.submitLoading = true;
      const res = await PluginStore.updateResourcePolicy({
        bk_biz_id: this.bizId,
        bk_obj_id: 'service_template',
        bk_inst_id: this.moduleId,
        resource_policy: this.pluginList.map(({ plugin_name }) => ({
          plugin_name,
          cpu: this.formData[`${plugin_name}_cpu`],
          mem: this.formData[`${plugin_name}_mem`],
        })),
      });
      const taskIds = res.job_id_list;
      if (taskIds.length) {
        this.$router.push({ name: 'taskList', params: { taskIds } });
      }
      this.submitLoading = false;
    });
  }
  public handleFormReset() {
    this.resourceForm && this.resourceForm.clearError();
    this.formatFormData();
  }
  public formatFormData() {
    const formData: { [key: string]: number } = {};
    const nameMap: { [key: string]: string } = {};
    this.pluginList.forEach(({ plugin_name, cpu, mem }) => {
      const cpuKey = `${plugin_name}_cpu`;
      const memKey = `${plugin_name}_mem`;
      formData[cpuKey] = cpu || 0;
      formData[memKey] = mem || 0;
      nameMap[cpuKey] = plugin_name;
    });
    this.$set(this, 'formData', formData);
  }
  public handleBack() {
    this.$router.replace({
      name: 'resourceQuota',
      query: this.$route.query,
    });
  }
}
</script>

<style lang="postcss" scoped>
.resource-quota-edit {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 52px);
  padding: 20px 24px;

  .page-body {
    flex: 1;
    display: flex;
    padding: 4px 22px 0 22px;
  }
  .content-body {
    flex: 1;
    padding: 20px 24px;
    overflow: hidden;
    .content-body-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 24px;
    }
  }
  .form-head {
    display: flex;
    line-height: 32px;
    margin-bottom: 16px;
    .form-head-item {
      padding: 0 10px;
      background: #EAEBF0;
      border-right: 1px solid #FFF;
      color: #313238;
      &:nth-child(2) {
        width: 215px;
      }
      &:last-child {
        width: 200px;
        border-right: 0;
      }
    }
    .text-underline-dashed {
      border-bottom: 1px dashed #c4c6cc;
      cursor: default;
    }
  }
  .form-horizontal-item {
    display: flex;
    .bk-form-item:first-child {
      flex: 1;
    }
    .bk-form-item:nth-child(2) {
      margin: 0;
      width: 216px;
      /deep/ .bk-form-content {
        margin: 0px;
      }
    }
    .group-text {
      width: 32px;
      padding: 0;
      text-align: center;
    }
    & + .form-horizontal-item {
      margin-top: 24px;
    }
  }
  .form-btn-group {
    margin-top: 32px;
    font-size: 0;
    .action-btn {
      min-width: 88px;
      margin-right: 8px;
    }
  }
}
</style>
