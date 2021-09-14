<template>
  <div v-bkloading="{ isLoading: loading }">
    <bk-table
      :data="tableList"
      class="plugin-version-table"
      :max-height="windowHeight - 112"
      :row-style="getRowStyle">
      <bk-table-column :label="$t('程序版本')" class-name="first-cell" prop="version" sortable width="100">
      </bk-table-column>
      <bk-table-column :label="$t('主配置版本')" prop="mainConfigVersion" sortable></bk-table-column>
      <bk-table-column :label="$t('子配置模板')" class-name="config-cell" min-width="150" sortable>
        <template #default="{ row }">
          <ul class="config-list" v-if="row.childConfigTemplates && row.childConfigTemplates.length">
            <li class="config-item" v-for="(template, index) in row.childConfigTemplates" :key="index">
              <span class="config-item-name" :title="template.name">{{ template.name }}</span>
              <span class="ml10 config-item-version">{{ template.version }}</span>
            </li>
          </ul>
          <span v-else>--</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('包大小')" prop="pkg_size" width="80" sortable></bk-table-column>
      <bk-table-column :label="$t('更新时间')" prop="pkg_mtime" min-width="110" sortable>
        <template #default="{ row }">
          {{ row.pkg_mtime | filterTimezone }}
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('更新人')" prop="creator" width="100" sortable></bk-table-column>
      <bk-table-column :label="$t('状态')" sortable width="75">
        <template #default="{ row }">
          <span v-if="!row.is_ready" class="tag-switch tag-indeterminate">{{ $t('停用') }}</span>
          <span
            v-else
            :class="[
              'tag-switch',
              { 'tag-enable': row.is_release_version, 'tag-yellow': !row.is_release_version }
            ]">
            {{ row.is_release_version ? $t('正式') : $t('测试') }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('操作')" width="100">
        <template #default="{ row }">
          <div v-if="row.operateLoading">
            <loading-icon></loading-icon>
            <span class="loading-text ml5">{{ $t('正在变更') }}</span>
          </div>
          <bk-popover
            theme="light agent-operate"
            trigger="click"
            :arrow="false"
            offset="30, 5"
            placement="bottom"
            :tippy-options="{
              boundary: 'window'
            }"
            v-else>
            <bk-button v-test="'statusChange'" theme="primary" text>{{ $t('更改状态') }}</bk-button>
            <template #content>
              <ul class="dropdown-list" v-test="'statusUL'">
                <li v-for="item in operateList"
                    :key="item.id"
                    :class="['list-item', { 'disabled': getOperateDisabled(row, item) }]"
                    v-bk-tooltips.left="{
                      content: item.tips,
                      disabled: !item.tips || getOperateDisabled(row, item)
                    }"
                    @click="!getOperateDisabled(row, item) && handleOperate(row, item.id)">
                  {{ item.name }}
                </li>
              </ul>
            </template>
          </bk-popover>
        </template>
      </bk-table-column>
    </bk-table>
  </div>
</template>
<script lang="ts">
import { Component, Prop, Watch, Mixins } from 'vue-property-decorator';
import { MainStore, PluginStore } from '@/store';
import pollMixin from '@/common/poll-mixin';
import { IPkVersionRow } from '@/types/plugin/plugin-type';
import { IOperateItem } from '@/types/agent/agent-type';

@Component({
  name: 'plugin-version-table',
})
export default class PackageVersion extends Mixins(pollMixin) {
  @Prop({ default: 0, type: [String, Number] }) private readonly id!: number|string;
  @Prop({ default: '', type: String }) private readonly os!: string;
  @Prop({ default: '', type: String }) private readonly cpuArch!: string;

  private loading = false;
  private tableList: IPkVersionRow[] = [];
  private operateList: IOperateItem[] = [];

  private get windowHeight() {
    return MainStore.windowHeight;
  }

  @Watch('id', { immediate: true })
  private handlePkgIdChange(id: number) {
    this.getVersionHistory(id);
  }

  private created() {
    this.operateList = [
      {
        id: 'release',
        name: this.$t('正式'),
      },
      {
        id: 'offline',
        name: this.$t('测试'),
        tips: this.$t('测试版本要主动选择才能安装'),
      },
      {
        id: 'stop',
        name: this.$t('停用'),
        tips: this.$t('停用版本不可以被部署到新的主机上'),
      },
    ];
  }

  public async getVersionHistory(id: number) {
    this.loading = true;
    this.tableList = await PluginStore.versionHistory({ pk: `${id}`, params: { os: this.os, cpu_arch: this.cpuArch } });
    this.loading = false;
  }

  public async handleOperate(row: IPkVersionRow, type: 'release' | 'offline' | 'stop') {
    row.operateLoading = true;
    const { id, version, md5 } = row;
    const params = {
      operation: type,
      id: [id], // 监控历史遗留 - 批量
      version,
      os: this.os,
      md5_list: md5 ? [md5] : [],  // 监控历史遗留 - 批量
    };
    console.log(params);
    const res = await PluginStore.packageOperation(params);
    if (res.find((item: number) => item === id)) { // 返回的也是个数组
      switch (type) {
        case 'release':
        case 'offline':
          row.is_release_version = type === 'release';
          row.is_ready = true;
          break;
        case 'stop':
          row.is_ready = false;
          break;
        default:
          break;
      }
      this.$emit('version-change');
    }
    row.operateLoading = false;
  }
  private getRowStyle({ row }: { row: IPkVersionRow }) {
    return row.is_ready ? {} : { color: '#C4C6CC' };
  }
  private getOperateDisabled(row: IPkVersionRow, item: IOperateItem) {
    if (!row.is_ready) {
      return item.id === 'stop';
    }
    return (row.is_release_version && item.id === 'release') || (!row.is_release_version && item.id === 'offline');
  }
}
</script>

<style lang="postcss" scoped>
  .plugin-version-table {
    >>> .cell {
      padding-left: 10px;
      padding-right: 10px;
    }
    >>> .first-cell .cell {
      padding-left: 20px;
    }
    .config-cell {
      .config-list {
        display: inline-block;
        padding: 10px 0;
        line-height: 20px;
        max-width: 100%;
      }
      .config-item {
        display: flex;
        width: 100%;
        min-width: 110px;
      }
      .config-item-name {
        flex: 1;
        display: inline-block;
        height: 20px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap
      }
    }
    .loading-text {
      color: #3a84ff;
    }
    .operate-btn {
      min-width: 30px;
    }
  }
</style>
