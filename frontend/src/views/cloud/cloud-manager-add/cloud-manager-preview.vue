<template>
  <article class="edit-cloud-preview" v-bkloading="{ isLoading: loading }" v-test.cloudInfo="'cloudInfo'">
    <div class="table-header">
      <div class="table-header-left">
        <span class="package-name">{{ $t('重装Proxy') }}</span>
        <i18n path="机器数量" class="package-selection">
          <span class="selection-num">{{ totalNum }}</span>
        </i18n>
      </div>
      <div class="table-header-right">
        <template v-for="(item, index) in statisticsList">
          <i18n :path="item.path" :key="index">
            <span :class="['filter-num', item.id]">{{ item.count }}</span>
          </i18n>
          <span v-if="index < (statisticsList.length - 1)" class="mr5" :key="`separator-${index}`">,</span>
        </template>
      </div>
    </div>
    <bk-table
      class="preview-table"
      :data="proxyList"
      :header-border="false">
      <bk-table-column label="Proxy IP">
        <template #default="{ row }">
          <bk-button v-test="'view'" text @click="handleViewProxy(row)" class="row-btn">
            {{ row.inner_ip }}
          </bk-button>
        </template>
      </bk-table-column>
      <bk-table-column
        key="login_ip"
        :label="$t('登录IP')"
        prop="login_ip">
        <template #default="{ row }">
          {{ row.login_ip || filterEmpty }}
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('归属业务')"
        prop="bk_biz_name" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.bk_biz_name | filterEmpty }}</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('Proxy状态')" prop="status">
        <template #default="{ row }">
          <div class="col-status" v-if="statusMap[row.status]">
            <span :class="'status-mark status-' + row.status"></span>
            <span>{{ statusMap[row.status] }}</span>
          </div>
          <div class="col-status" v-else>
            <span class="status-mark status-unknown"></span>
            <span>{{ $t('未知') }}</span>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('密码密钥')" prop="re_certification">
        <template #default="{ row }">
          <span :class="['tag-switch', { 'tag-enable': !row.re_certification }]">
            {{ row.re_certification ? $t('过期') : $t('有效') }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('Proxy版本')" prop="version">
        <template #default="{ row }">
          <span>{{ row.version | filterEmpty }}</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('Agent数量')" prop="pagent_count">
        <template #default="{ row }">
          <span
            class="link-pointer"
            v-if="row.pagent_count"
            @click="$router.push({
              name: 'agentStatus',
              params: { cloud: { id, name: formData.bkCloudName } }
            })">
            {{ row.pagent_count }}
          </span>
          <span v-else>0</span>
        </template>
      </bk-table-column>
    </bk-table>
    <!--操作按钮-->
    <section class="add-cloud-footer mt30">
      <bk-button
        theme="primary"
        ext-cls="nodeman-primary-btn"
        :loading="loadingSubmitBtn"
        @click="handleCommit">
        {{ $t('立即执行') }}
      </bk-button>
      <bk-button class="nodeman-cancel-btn ml10" @click="routerBack">{{ $t('上一步') }}</bk-button>
      <bk-button class="nodeman-cancel-btn ml10" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </section>

    <!--侧栏详情-->
    <CloudDetailSlider
      v-model="showSlider"
      :row="currentRow">
    </CloudDetailSlider>
  </article>
</template>
<script lang="ts">
import { Component, Prop } from 'vue-property-decorator';
import { CloudStore } from '@/store/index';
import RouterBackMixin from '@/common/router-back-mixin';
import CloudDetailSlider from '../cloud-manager-detail/cloud-detail-slider.vue';
import { IProxyDetail } from '@/types/cloud/cloud';

@Component({
  name: 'cloud-manager-preview',
  components: {
    CloudDetailSlider,
  },
})
export default class CloudManagerPreview extends RouterBackMixin {
  @Prop({ type: Number, default: 0 }) private readonly id!: number;
  @Prop({ type: String, default: 'edit' }) private readonly type!: string;
  @Prop({ type: Object, default: () => ({}) }) private readonly formData!: any;

  private loadingProxy = false;
  private loadingSubmitBtn = false;
  private proxyList: IProxyDetail[] = [];
  private showSlider = false;
  private currentRow: Dictionary = {};
  private totalNum = 0;
  private runningNum = 0;
  private terminatedNum = 0;
  private notInstalledNum = 0;
  // 状态map
  private statusMap = {
    running: this.$t('正常'),
    terminated: this.$t('异常'),
    not_installed: this.$t('未安装'),
    unknown: this.$t('未知'),
  };

  private get statisticsList() {
    return [
      { id: 'running', count: this.runningNum, path: '正常agent个数' },
      { id: 'terminated', count: this.terminatedNum, path: '异常agent个数' },
      { id: 'not_installed', count: this.notInstalledNum, path: '未安装agent个数' },
    ].filter(item => !!item.count);
  }

  private created() {
    this.handleGetProxyList();
  }
  /**
     * 获取云区域Proxy列表
     */
  public async handleGetProxyList() {
    this.loadingProxy = true;
    this.proxyList = await CloudStore.getCloudProxyList({ bk_cloud_id: this.id });
    this.totalNum = this.proxyList.length;
    this.runningNum = this.proxyList.filter(item => item.status === 'running').length;
    this.terminatedNum = this.proxyList.filter(item => item.status === 'terminated').length;
    this.notInstalledNum = this.proxyList.filter(item => item.status === 'not_installed').length;
    this.loadingProxy = false;
  }

  public async handleCommit() {
    this.loadingSubmitBtn = true;
    const editSuccess = await this.handleUpdateCloud();
    if (editSuccess) {
      await this.handleReinstall();
    }
    this.loadingSubmitBtn = false;
  }
  public async handleUpdateCloud() {
    this.loadingSubmitBtn = true;
    const res = await CloudStore.updateCloud({
      pk: this.id as number,
      params: {
        bk_cloud_name: this.formData.bkCloudName,
        isp: this.formData.isp,
        ap_id: this.formData.apId as number,
      },
    });
    return Promise.resolve(res);
  }
  public async handleReinstall() {
    this.loadingProxy = true;
    const result = await CloudStore.operateJob({
      job_type: 'REINSTALL_PROXY',
      bk_host_id: this.proxyList.map(item => item.bk_host_id),
    });
    this.loadingProxy = false;
    if (result.job_id) {
      this.$router.push({
        name: 'taskDetail',
        params: { taskId: result.job_id },
      });
    }
  }

  public handleViewProxy(row: IProxyDetail) {
    this.showSlider = true;
    this.currentRow = row;
  }
  /**
   * 取消
   */
  public handleCancel() {
    this.$router.push({ name: 'cloudManager' });
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";
  .table-header {
    padding: 0 24px;
    margin-bottom: -1px;
    height: 42px;
    background: #f0f1f5;
    border: 1px solid #dcdee5;
    border-radius: 2px 2px 0 0;

    @mixin layout-flex row, center, space-between;
    &-left {
      font-weight: Bold;
      .package-selection {
        color: #979ba5;
      }
    }
    &-right {
      .filter-num {
        font-weight: bold;
        cursor: pointer;
      }
    }
  }
</style>
