<template>
  <bk-form ref="form" class="upgrade-version pb30" v-bkloading="{ isLoading: loading }">
    <bk-form-item :label="$t('升级版本')" required>
      <bk-table
        :data="data"
        :span-method="handleSpanMerge"
        :row-class-name="handleRowClass"
        :cell-class-name="handleCellClass">
        <bk-table-column width="60" :render-header="renderRowSelect">
          <template #default="{ row }">
            <bk-checkbox
              v-bk-tooltips="{
                placement: 'left',
                content: '已经部署最新版本',
                disabled: !row.disabled,
                boundary: 'window'
              }"
              :checked="row.checked"
              :disabled="row.disabled"
              @change="handleCheck(row)">
            </bk-checkbox>
          </template>
        </bk-table-column>
        <NmColumn min-width="160" :label="$t('操作系统')" prop="support_os_cpu"></NmColumn>
        <NmColumn min-width="100" :label="$t('当前版本')" prop="current_version"></NmColumn>
        <NmColumn min-width="130" :label="$t('已部署数')" align="right" prop="nodes_number"></NmColumn>
        <NmColumn min-width="40"></NmColumn>
        <NmColumn min-width="120" :label="$t('选择目标版本')" prop="version">
          <template #default="{ row }">
            <div v-if="row.is_latest" class="target-text">{{ $t('已经部署最新版本') }}</div>
            <div v-else class="target-version" v-bk-tooltips.top="$t('选择版本')" @click="handleShowVersionDetail(row)">
              <bk-button text>
                {{ row.selectedVersion }}
                <span
                  class="tag-switch tag-yellow"
                  v-if="row.versionTarget && row.versionTarget.is_release_version === false">
                  {{ $t('测试') }}
                </span>
              </bk-button>
            </div>
          </template>
        </NmColumn>
        <NmColumn
          :label="$t('版本描述')"
          class-name="td-description"
          min-width="350"
          prop="version_scenario">
          <div slot-scope="{ row }" class="cell-description" :style="{ '-webkit-line-clamp': row.rowspan }">
            {{ row.version_scenario }}
          </div>
        </NmColumn>
      </bk-table>
    </bk-form-item>
    <bk-form-item>
      <bk-popover placement="top" :disabled="isCheckedIndeterminate || isCheckedAll">
        <bk-button
          class="nodeman-primary-btn"
          theme="primary"
          :disabled="historyLoading || (!isCheckedIndeterminate && !isCheckedAll)"
          @click="handleNext">
          {{ $t('下一步') }}
        </bk-button>
        <div slot="content">{{ $t('插件配置不能为空') }}</div>
      </bk-popover>
      <bk-button
        class="nodeman-cancel-btn ml5"
        @click="handleStepCancel">
        {{ $t('取消') }}
      </bk-button>
    </bk-form-item>
    <VersionDetailTable
      v-model="showVersionDetail"
      :loading="dialogLoading"
      :version="dialogRow.selectedVersion"
      :data="pkVersionData"
      @target-change="handleTargetChange">
    </VersionDetailTable>
  </bk-form>
</template>
<script lang="ts">
import { Component, Mixins, Ref, Emit, Prop } from 'vue-property-decorator';
import { CreateElement } from 'vue';
import { PluginStore } from '@/store';
import FormLabelMixin from '@/common/form-label-mixin';
import VersionDetailTable from './version-detail-table.vue';
import { IBkColumn } from '@/types';
import { IPk, IPkVersionRow, IVersionRow } from '@/types/plugin/plugin-type';

@Component({
  name: 'upgrade-version',
  components: {
    VersionDetailTable,
  },
})
export default class UpgradeVersion extends Mixins(FormLabelMixin) {
  @Prop({ default: '', type: [String, Number] }) private readonly id!: string | number;
  @Ref('form') private readonly form!: any;

  private loading = false;
  private dialogLoading = false;
  private historyLoading = false;
  private showVersionDetail = false;
  private data: IVersionRow[] = [];
  private pkVersionData: IPkVersionRow[] = [];
  private dialogRow: Dictionary = {};

  private get isCheckedAll() {
    return !!this.data.length && this.data.every(row => row.disabled || row.checked)
        && !this.data.every(row => row.disabled);
  }
  private get isCheckedIndeterminate() {
    return !this.isCheckedAll && this.data.some(row => !row.disabled && row.checked);
  }
  private get isAllDisabled() {
    return this.data.every(item  => item.is_latest);
  }

  private mounted() {
    this.minWidth = 86;
    this.initLabelWidth(this.form);
    this.getPkConfigTable();
  }

  @Emit('cancel')
  public handleStepCancel() {}
  @Emit('next')
  public handleNext() {
    const copyConfigs: IPk[] = JSON.parse(JSON.stringify(PluginStore.strategyData.configs || []));
    // 使用rowspan做去重
    const selectedConfigs = this.data.filter(row => row.checked && row.rowspan && !row.disabled)
      .map(row => row.versionTarget as IPk);
    selectedConfigs.forEach((item) => {
      if (!item) return;
      const index = copyConfigs.findIndex(config => config.support_os_cpu === item.support_os_cpu);
      if (index > -1) {
        copyConfigs.splice(index, 1, item);
      } else {
        copyConfigs.push(item);
      }
    });
    PluginStore.setStateOfStrategy({ key: 'configs', value: copyConfigs }); // 需要把选中的目标替换
  }

  public async getPkConfigTable() {
    this.loading = true;
    const res = await PluginStore.pkConfigList(this.id as number);
    const list: IVersionRow[] = [];
    res.forEach((item: any) => {
      if (item.current_version_list?.length) {
        const rowspan = item.current_version_list.length;
        item.current_version_list.forEach((row: IVersionRow, index: number) => {
          list.push({
            ...row,
            checked: !item.is_latest,
            disabled: !!item.is_latest,
            current_version: row.current_version || '--',
            is_latest: item.is_latest,
            latest_version: item.latest_version,
            selectedVersion: item.latest_version,
            versionTarget: undefined, // 切换之后的目标
            version_scenario: item.version_scenario,
            support_os_cpu: `${row.os} ${row.cpu_arch}`,
            rowspan: index ? 0 : rowspan,
          });
        });
      }
    });
    list.sort((prev, next) => Number(prev.is_latest) - Number(next.is_latest));
    this.data = list;
    this.preloadingHistory(res);
    this.loading = false;
  }
  public handleCheckAll(checked: boolean) {
    this.data.forEach((row) => {
      if (!row.disabled) {
        row.checked = checked;
      }
    });
  }
  public handleCheck(row: IVersionRow) {
    row.checked = !row.checked;
    // 相同条件的版本需要全部勾选
    this.data.forEach((item: any) => {
      if (row.support_os_cpu === item.support_os_cpu) {
        item.checked = row.checked;
      }
    });
  }
  public renderRowSelect(h: CreateElement) {
    return h('bk-checkbox', {
      props: {
        indeterminate: this.isCheckedIndeterminate,
        checked: this.isCheckedAll,
        disabled: this.isAllDisabled,
      },
      on: {
        change: this.handleCheckAll,
      },
    });
  }

  public handleSpanMerge({ column, row }: { column: IBkColumn, row: IVersionRow }) {
    if (column.property === 'version' || column.property === 'version_scenario') {
      return {
        rowspan: row.rowspan,
        colspan: row.is_latest && column.property === 'version' ? 2 : 1,
      };
    }
    return {
      rowspan: 1,
      colspan: 1,
    };
  }

  public handleRowClass({ row }: { row: IVersionRow }) {
    return row.disabled ? 'disabled-row' : '';
  }

  public handleCellClass({ column }: {column: IBkColumn}) {
    if (column.property === 'version') {
      return 'version-cell table-cell';
    }
    return '';
  }

  public handleShowVersionDetail(row: IVersionRow) {
    this.showVersionDetail = true;
    this.dialogRow = row;
    this.getPkVersionData(row);
  }

  public handleTargetChange(versionTarget: IPkVersionRow) {
    const list = this.data.filter(row => row.support_os_cpu === this.dialogRow.support_os_cpu);
    list.forEach((row) => {
      row.versionTarget = versionTarget;
      row.selectedVersion = versionTarget.version;
    });
    this.pkVersionData = [];
    this.showVersionDetail = false;
  }
  public async getPkVersionData(row: IVersionRow) {
    this.dialogLoading = true;
    const res = await PluginStore.versionHistory({
      pk: `${PluginStore.strategyData.plugin_info?.id}`,
      params: { os: row.os, cpu_arch: row.cpu_arch },
    });
    this.pkVersionData = res.map(item => ({
      ...item,
      // is_ready - 启用, is_release_version - 上线
      disabled: item.version < row.current_version || !(item.is_ready && item.is_release_version),
      isBelowVersion: item.version < row.current_version || !(item.is_ready && item.is_release_version),
    }));
    this.dialogLoading = false;
  }

  // 预加载 并 选中最新版本
  public preloadingHistory(data: IVersionRow[]) {
    const promiseList: any[] = [];
    data.forEach((row) => {
      if (!row.is_latest) {
        promiseList.push(new Promise(async (resolve, reject) => await PluginStore.versionHistory({
          pk: `${PluginStore.strategyData.plugin_info?.id}`,
          params: { os: row.os, cpu_arch: row.cpu_arch },
        })
          .then(res => resolve({
            sys: `${row.os} ${row.cpu_arch}`,
            data: res,
          }))
          .catch(err => reject(err))));
      }
    });
    this.historyLoading = true;
    Promise.all(promiseList).then((res) => {
      this.data.forEach((row) => {
        if (!row.is_latest) {
          const history = res.find((item: { sys: string, data: any[] }) => row.support_os_cpu === item.sys);
          if (history?.data) {
            const latest = history.data.find((item: any) => item.version === row.latest_version);
            row.versionTarget = latest || {};
          }
        }
      });
      this.historyLoading = false;
    });
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-dialog {
  &-body {
    padding: 0;
    height: 500px;
  }
  &-footer {
    border-top: 0;
  }
}
>>> .bk-table-body {
  tr:hover {
    background-color: #fff;
  }
  tr:hover>td {
    background-color: #fff;
  }
}
>>> .disabled-row {
  color: #c4c6cc;
}
>>> .version-cell {
  border-left: 1px solid #dfe0e5;
  border-right: 1px solid #dfe0e5;
  .cell {
    height: 100%;
  }
  .bk-button-text {
    position: relative;
  }
  .tag-yellow {
    position: absolute;
    top: 1px;
    left: 100%;
    line-height: 18px;
    margin-left: 6px;
    white-space: nowrap;
  }
}
>>> .table-cell:hover {
  /* stylelint-disable-next-line declaration-no-important */
  background-color: #f0f1f5 !important;
}
.upgrade-version {
  padding-right: 24px;
}
.target-version {
  height: 100%;
  line-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
>>> .td-description .cell {
  line-height: 22px;
  -webkit-line-clamp: inherit;
}
.cell-description {
  /* stylelint-disable */
  display: -webkit-box;
  -webkit-box-orient: vertical;
  /* stylelint-enable */
}
.target-text {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  height: 100%;
}
</style>
