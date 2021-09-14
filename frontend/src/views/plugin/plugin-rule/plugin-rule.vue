<template>
  <div v-test="'policy'">
    <PluginRuleOperate
      :search-values="searchSelectValue"
      :created-operate="authority.operate"
      @value-change="handleSearchValueChange"
      @strategy-change="handleStrategyChange"
      @biz-change="handleGetPluginRules">
    </PluginRuleOperate>
    <PluginRuleTable
      class="mt15"
      v-bkloading="{ isLoading: loading }"
      :data="data"
      :pagination="pagination"
      :delete-id="deleteId"
      :filter-list="filterData"
      @more-operate="handleMoreOperate"
      @page-change="handlePageChange"
      @limit-change="handleLimitChange"
      @filter-confirm="handleFilterChange"
      @filter-reset="handleFilterChange"
      @expand-change="handleExpandChange">
    </PluginRuleTable>
    <bk-dialog
      header-position="left"
      ext-cls="stop-policy-dialog"
      :width="480"
      :mask-close="false"
      :value="dialogInfo.visible"
      :title="dialogInfo.title"
      @cancel="dialogInfo.visible = false">
      <template #default>
        <tips class="mb15" :list="$t('停用策略Tips')"></tips>
        <bk-radio-group v-model="dialogInfo.onlyDisabled">
          <div>
            <bk-radio v-test="'stopPolicy'" :value="true">
              <i18n path="停用策略dialogContentOnly"><b class="focus-stag">{{ $t('运行中') }}</b></i18n>
            </bk-radio>
          </div>
          <div class="mt10">
            <bk-radio v-test="'stopPlugin'" :value="false">
              <i18n path="停用策略dialogContentAll"><b class="focus-stag">{{ $t('停用') }}</b></i18n>
            </bk-radio>
          </div>
        </bk-radio-group>
      </template>
      <template #footer>
        <div class="footer">
          <bk-button
            v-test.common="'formCommit'" theme="primary" :loading="dialogInfo.loading" @click="handleDialogConfirm">
            {{ $t('确定') }}
          </bk-button>
          <bk-button class="ml10" @click="dialogInfo.visible = false">{{ $t('取消') }}</bk-button>
        </div>
      </template>
    </bk-dialog>
  </div>
</template>
<script lang="ts">
import { Mixins, Component } from 'vue-property-decorator';
import { MainStore, PluginStore } from '@/store';
import PluginRuleOperate from './plugin-rule-list/plugin-rule-operate.vue';
import PluginRuleTable from './plugin-rule-list/plugin-rule-table.vue';
import Tips from '@/components/common/tips.vue';
import { IPolicyRow, IPluginRuleParams } from '@/types/plugin/plugin-type';
import { IPagination, ISearchItem, ISearchChild } from '@/types';
import { debounceDecorate } from '@/common/util';
import authorityMixin from '@/common/authority-mixin';
import pollMixin from '@/common/poll-mixin';

@Component({
  name: 'plugin-rule',
  components: {
    PluginRuleOperate,
    PluginRuleTable,
    Tips,
  },
})
export default class PluginRule extends Mixins(authorityMixin(), pollMixin) {
  private data: IPolicyRow[] = [];
  private pagination: IPagination = {
    current: 1,
    count: 0,
    limit: 20,
  };
  private searchSelectValue = '';
  private strategy: string | number = '';
  private loading = false;
  private deleteId = -1;
  private dialogInfo: Dictionary = {
    loading: false,
    title: '',
    visible: false,
    row: null,
    onlyDisabled: true,
  };
  private filterData: ISearchItem[] = [{
    name: window.i18n.t('策略状态'),
    id: 'enable',
    children: [
      { name: window.i18n.t('启用'), id: 'true', checked: false },
      { name: window.i18n.t('停用'), id: 'false', checked: false },
    ],
    multiable: false,
  }];

  private get selectedBiz() {
    return MainStore.selectedBiz;
  }

  private created() {
    const name = this.$route.params.name || this.$route.query.name as string;
    this.searchSelectValue = name || '';
    this.handleGetPluginRules();
  }

  private async handleGetPluginRules() {
    this.loading = true;
    this.runingQueue.splice(0, this.runingQueue.length);
    const params = this.getParams();
    const res = await PluginStore.getPluginRules(params);
    const list = res.list as IPolicyRow[];
    const tableData: IPolicyRow[] = [];
    const expandRow: IPolicyRow[] = [];
    list.forEach((row) => {
      const item = {
        ...row,
        hasGrayRule: row.children && !!row.children.length,
        expand: false,
        abnormal_host_ids: [],
        abnormal_host_count: 0,
        children: (row.children || []).map(child => ({
          abnormal_host_ids: [], // 初始化灰度的异常信息
          abnormal_host_count: 0,
          ...child,
          enable: ['PENDING', 'RUNNING'].includes(row.job_result.status) ? false : row.enable,
          isGrayRule: true,
        })),
      };
      tableData.push(item);
      // 有搜索条件默认展开
      if ((!!row.expand || !!params.conditions?.find(item => item.key === 'query')) && item.hasGrayRule) {
        expandRow.push(item);
      }
    });
    this.data = tableData;
    expandRow.forEach((item) => {
      this.handleExpandChange(item);
    });
    const policyIds: number[] = [];
    const statusList = ['PENDING', 'RUNNING'];
    this.data.forEach((row: IPolicyRow) => {
      if (!row.isGrayRule && row.job_result && statusList.includes(row.job_result.status)) {
        policyIds.push(row.id);
      }
      if (row.children && row.children.length) {
        const gray = row.children.filter(item => item.job_result && statusList.includes(item.job_result.status))
          .map(item => item.id);
        policyIds.push(...gray);
      }
    });
    this.runingQueue = Array.from(new Set(policyIds));
    this.pagination.count = res.total;
    this.getFetchPolicyAbnormalInfo();
    this.loading = false;
  }
  /**
   * 运行轮询任务
   */
  public async handlePollData() {
    const { list } = await PluginStore.getPluginRules({
      page: 1,
      pagesize: -1,
      conditions: [
        { key: 'id', value: this.runingQueue },
      ],
      only_root: false,
    });
    if (list.length) {
      this.findAndResetRow(this.data.filter(row => !row.isGrayRule), list as IPolicyRow[]);
    }
  }
  // 获取策略的错误提示信息
  public async getFetchPolicyAbnormalInfo() {
    const policyIds: number[] = []; //
    this.data.forEach((row) => {
      if (row.enable) {
        policyIds.push(row.id);
        if (row.children?.length) {
          policyIds.push(...row.children.map(child => child.id));
        }
      }
    });
    const res = await PluginStore.getFetchPolicyAbnormalInfo({ policy_ids: policyIds });
    const idKeys = Object.keys(res);
    this.data.forEach((row) => {
      const idStr = `${row.id}`;
      if (!row.isGrayRule && idKeys.includes(idStr)) {
        row.abnormal_host_count = res[idStr].abnormal_host_count;
        row.abnormal_host_ids = res[idStr].abnormal_host_ids;
      }
      if (row.children?.length) {
        row.children.forEach((child) => {
          const idStr = `${child.id}`;
          if (idKeys.includes(idStr)) {
            child.abnormal_host_count = res[idStr].abnormal_host_count;
            child.abnormal_host_ids = res[idStr].abnormal_host_ids;
          }
        });
      }
    });
  }

  @debounceDecorate(700)
  private handleSearchValueChange(v: string) {
    this.searchSelectValue = v;
    this.handleGetPluginRules();
  }

  private handleStrategyChange(id: string | number) {
    this.strategy = id;
    this.handleGetPluginRules();
  }

  private handlePageChange(newPage: number) {
    this.pagination.current = newPage;
    this.handleGetPluginRules();
  }

  private handleLimitChange(limit: number) {
    this.pagination.current = 1;
    this.pagination.limit = limit;
    this.handleGetPluginRules();
  }
  private handleFilterChange({ prop, list }: { prop: string, list: ISearchChild[] }) {
    const currentFilter = this.filterData.find(item => item.id === prop);
    if (currentFilter) {
      currentFilter.children = list || (currentFilter.children as ISearchChild[])
        .map(item => ({ ...item, checked: false }));
      this.handlePageChange(1);
    }
  }
  private handleExpandChange(row: IPolicyRow) {
    if (row.hasGrayRule && row.children && row.children.length) {
      row.expand = !row.expand;
      const rowIndex = this.data.findIndex(item => item.id === row.id);
      if (row.expand) {
        this.data.splice(rowIndex + 1, 0, ...row.children);
      } else {
        this.data.splice(rowIndex + 1, row.children.length);
      }
    }
  }

  private getParams() {
    const { current, limit } = this.pagination;
    const params: IPluginRuleParams = {
      page: current,
      pagesize: limit,
    };
    if (this.searchSelectValue) {
      params.conditions = [{ key: 'query', value: this.searchSelectValue }];
    }
    if (this.selectedBiz && this.selectedBiz.length) {
      params.bk_biz_ids = this.selectedBiz;
    }
    const children = this.filterData[0].children as ISearchChild[];
    const statusChild = children.find(item => item.checked);
    if (statusChild && !children.every(item => item.checked)) {
      const enableItem = {
        key: 'enable',
        value: statusChild.id === 'true',
      };
      if (params.conditions) {
        params.conditions.push(enableItem);
      } else {
        params.conditions = [enableItem];
      }
    }
    return params;
  }

  private handleMoreOperate({ row, type }: { row: IPolicyRow, type: string }) {
    // RETRY_ABNORMAL delete stop
    if (type === 'delete') {
      this.deletePolicy(row, type);
    } else if (type === 'stop') {
      this.dialogInfo.visible = true;
      this.dialogInfo.onlyDisabled = true;
      this.dialogInfo.row = row;
      this.dialogInfo.title = this.$t('停用策略dialogTitle', [row.name]);
    } else {
      this.goOperatePreviewPage(row, type);
    }
  }
  private handleDialogConfirm() {
    const { onlyDisabled, row } = this.dialogInfo;
    if (onlyDisabled) {
      this.onlyStopPolicy(row, 'stop'); // 仅停用策略
    } else {
      this.goOperatePreviewPage(row, 'stop'); // 策略及插件都停用
    }
  }

  private goOperatePreviewPage(row: IPolicyRow, type: string) {
    this.$router.push({
      name: 'createRule',
      params: { type, id: row.id, policyName: row.name, pluginName: row.plugin_name },
    });
  }

  // 仅停用策略 不停用插件
  private async onlyStopPolicy(row: IPolicyRow, type: string) {
    this.dialogInfo.loading = true;
    const res = await PluginStore.operatePolicy({
      policy_id: row.id,
      op_type: type.toUpperCase(),
      only_disable: true,
    });
    this.dialogInfo.loading = false;
    if (res.updated) {
      row.enable = false;
      if (row.children) {
        row.children.forEach((item) => {
          item.enable = row.enable;
        });
      }
      this.dialogInfo.visible = false;
      this.$bkMessage({
        theme: 'success',
        message: this.$t('停用策略成功'),
      });
    }
  }
  private async deletePolicy(row: IPolicyRow, type: string) {
    this.deleteId = row.id;
    const res = await PluginStore.operatePolicy({
      policy_id: row.id,
      op_type: type.toUpperCase(),
    });
    if (res.deleted) {
      this.$bkMessage({
        theme: 'success',
        message: this.$t('删除策略成功'),
      });
      this.handlePageChange(1);
    }
    this.deleteId = -1;
  }
  // 设置策略的任务执行状态 和 启用状态
  private findAndResetRow(tableData: IPolicyRow[], list: IPolicyRow[]) {
    tableData.forEach((row) => {
      const newRow = list.find(item => item.id === row.id);
      if (newRow) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { children, expand, ...attr } = newRow as IPolicyRow;
        if (!['PENDING', 'RUNNING'].includes(newRow.job_result.status)) {
          const i = this.runingQueue.findIndex(id => id === newRow.id);
          i > -1 && this.runingQueue.splice(i, 1);
        }
        Object.assign(row, attr);
      }
      // 同步主策略与灰度策略的启停状态
      if (row.children && row.children.length) {
        row.children.forEach((item) => {
          item.enable = ['PENDING', 'RUNNING'].includes(row.job_result.status) ? false : row.enable;
        });
        this.findAndResetRow(row.children, list);
      }
    });
    // 重新拉取一下策略的异常信息
    if (!this.runingQueue.length) {
      this.getFetchPolicyAbnormalInfo();
    }
  }
}
</script>

<style lang="postcss" scoped>
  .stop-policy-dialog {
    .focus-stag {
      color: #63656e;
    }
  }
</style>
