<template>
  <bk-table v-test.policy="'curVersionTable'" :data="tableData" ref="tableRef" @selection-change="handleSelectd">
    <bk-table-column v-if="showSelect" type="selection" :selectable="handleSelectable"></bk-table-column>
    <bk-table-column :label="$t('操作系统')" prop="support_os_cpu"></bk-table-column>
    <bk-table-column :label="showSelect ? $t('部署版本') : $t('目标版本')">
      <template #default="{ row, $index }">
        <span class="version"
              v-bk-tooltips.top="{
                content: '选择版本',
                delay: 300
              }"
              @click="handleShowDetail(row, $index)">
          {{ row.version }}
        </span>
      </template>
    </bk-table-column>
    <VersionDetailTable
      v-model="showVersionDetail"
      :loading="versionLoading"
      :version="currentRowVersion"
      :data="pkVersionData"
      @target-change="handleVersionChoose">
    </VersionDetailTable>
  </bk-table>
</template>
<script lang="ts">
import { Vue, Component, Ref, Emit, Watch, Prop } from 'vue-property-decorator';
import { PluginStore } from '@/store';
import VersionDetailTable from './version-detail-table.vue';
import { deepClone } from '@/common/util';
import { IPk, IPkVersionRow } from '@/types/plugin/plugin-type';

interface IDeployPk extends IPk {
  disabled?: boolean
  selection?: boolean
  'is_preselection'?: boolean
}

@Component({
  name: 'deploy-version-table',
  components: { VersionDetailTable },
})
export default class DeployVersionTable extends Vue {
  @Ref('tableRef') private readonly tableRef!: any;
  @Prop({ type: [Number, String], default: '' }) private readonly pluginId!: number | string;
  @Prop({ type: Array, default: () => ([]) }) private readonly data!: IDeployPk[];
  @Prop({ type: Array, default: () => ([]) }) private readonly selected!: IDeployPk[];
  @Prop({ type: Boolean, default: true }) private readonly showSelect!: boolean;

  private tableData: IDeployPk[] = [];
  private showVersionDetail = false;
  private versionLoading = false;
  private currentRow: IDeployPk | null  = null;
  private currentRowIndex = -1;
  private currentRowIsCheck = false; // 当前Row是否被勾选
  private changedRow: IDeployPk | null = null;
  private pkVersionData: IPkVersionRow[] = [];

  private get currentRowVersion() {
    if (this.changedRow) {
      return this.changedRow.version;
    }
    return this.currentRow ? this.currentRow.version : '';
  }
  private get rowId() {
    return this.tableData.map(item => item.id);
  }

  @Watch('data', { immediate: true, deep: true })
  private handleDataChange() {
    this.tableData = deepClone(this.data); // 将版本变化限制在父子组件内
    this.$nextTick(() => {
      this.tableData.forEach((item) => {
        this.tableRef.toggleRowSelection(item, item.selection);
      });
    });
  }

  @Emit('checked')
  public handleSelectd(selection: IDeployPk[]) {
    return selection;
  }

  public handleShowDetail(row: IDeployPk, index: number) {
    this.getPkVersionData(row);
    this.currentRow = row;
    this.currentRowIndex = index;
    this.currentRowIsCheck = !!this.selected.find(selected => row.id === selected.id);
    this.showVersionDetail = true;
  }
  public async getPkVersionData(row: IDeployPk) {
    this.versionLoading = true;
    const res = await PluginStore.versionHistory({
      pk: this.pluginId,
      params: { os: row.os, cpu_arch: row.cpu_arch },
    });
    this.pkVersionData = res.map(item => ({
      ...item,
      // is_ready - 启用, is_release_version - 上线
      disabled: !item.is_ready || !item.is_release_version,
      isBelowVersion: !item.is_ready || !item.is_release_version, // 此处任意选取一个版本
    }));
    this.versionLoading = false;
  }
  // 改变插件版本
  @Emit('version-change')
  public handleVersionChoose(row: IDeployPk) {
    this.changedRow = row;
    // 替换掉原本的row
    const oldRow = this.tableData[this.currentRowIndex];
    this.changedRow.disabled = oldRow.disabled;
    this.changedRow.selection = oldRow.selection;
    this.tableData.splice(this.currentRowIndex, 1, this.changedRow);
    this.tableData.forEach((item, index) => {
      this.tableRef.toggleRowSelection(item, index === this.currentRowIndex
        ? this.currentRowIsCheck : !!this.selected.find(selected => item.id === selected.id));
    });
    this.handleDialogCancel();
  }
  public handleDialogCancel() {
    this.changedRow = null;
    this.currentRow = null;
    this.currentRowIndex = -1;
    this.showVersionDetail = false;
    this.pkVersionData = [];
  }
  public handleSelectable(row: IDeployPk) {
    return !row.is_preselection;
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-table-header {
  th {
    background-color: #fafbfd;
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
>>> .bk-dialog {
  &-body {
    padding: 0;
    height: 500px;
  }
  &-footer {
    border-top: 0;
  }
}
.version {
  display: inline-block;
  width: 100px;
  line-height: 28px;
  border-radius: 2px;
  color: #3a84ff;
  cursor: pointer;
  margin-left: -10px;
  padding: 0 10px;
  &:hover {
    background: #f0f1f5;
  }
}
</style>
