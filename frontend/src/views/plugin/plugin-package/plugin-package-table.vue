<template>
  <section v-bkloading="{ isLoading }">
    <bk-table
      :class="`plugin-package-table head-customize-table ${fontSize}`"
      :max-height="tableMaxHeight"
      :data="tableData"
      :pagination="pagination"
      :row-class-name="rowClassName"
      :span-method="colspanHandle"
      @page-change="handlePageChange"
      @page-limit-change="handleLimitChange">
      <NmColumn
        :label="$t('插件名称')"
        prop="name"
        sortable
        :resizable="false"
        min-width="120" />
      <NmColumn
        :label="$t('插件别名')"
        sortable
        :resizable="false"
        min-width="115">
        <template #default="{ row }">
          <auth-component
            class="alias-text-btn"
            v-test="'viewPlugin'"
            :authorized="row.permissions.operate"
            :apply-info="[{
              action: 'plugin_pkg_operate',
              instance_id: row.id,
              instance_name: row.name
            }]"
            @click="handleViewPlugin(row)">
            {{ row.description | filterEmpty }}
          </auth-component>
        </template>
      </NmColumn>
      <NmColumn
        v-if="getColumnShowStatus('category')"
        :label="$t('开发商')"
        prop="category"
        sortable
        :resizable="false"
        min-width="100">
        <template #default="{ row }">
          {{ row.category | filterEmpty }}
        </template>
      </NmColumn>
      <NmColumn
        v-if="getColumnShowStatus('nodes_number')"
        :label="$t('已部署节点')"
        prop="nodes_number"
        sortable
        align="right"
        min-width="110"
        :resizable="false">
        <template #default="{ row }">
          <loading-icon v-if="numLoading"></loading-icon>
          <div class="num-link" v-else>
            <bk-button v-test="'filterNode'" v-if="row.nodes_number" text @click.stop="handleViewTarget(row)">
              {{ row.nodes_number }}
            </bk-button>
            <span v-else>0</span>
          </div>
        </template>
      </NmColumn>
      <NmColumn min-width="30" v-if="getColumnShowStatus('nodes_number')">
        <template #default="" />
      </NmColumn>
      <NmColumn
        v-if="getColumnShowStatus('source_app_code')"
        :label="$t('数据对接SaaS')"
        prop="source_app_code"
        :resizable="false"
        min-width="130">
        <template #default="{ row }">
          <bk-button
            text
            v-if="row.source_app_code"
            @click="handleGotoSaaS(row.system_link)">
            {{ row.source_app_code }}
          </bk-button>
          <span v-else>--</span>
        </template>
      </NmColumn>
      <NmColumn
        v-if="getColumnShowStatus('scenario')"
        :label="$t('插件描述')"
        prop="scenario"
        min-width="120"
        :resizable="false">
        <template #default="{ row }">
          {{ row.scenario | filterEmpty }}
        </template>
      </NmColumn>
      <NmColumn
        v-if="getColumnShowStatus('deploy_type')"
        :label="$t('部署方式')"
        prop="deploy_type"
        :resizable="false"
        min-width="130">
        <template #default="{ row }">
          {{ row.deploy_type | filterEmpty }}
        </template>
      </NmColumn>
      <NmColumn
        v-if="getColumnShowStatus('is_ready')"
        :label="$t('插件状态')"
        prop="is_ready"
        min-width="100"
        :resizable="false">
        <template #default="{ row }">
          <span :class="['tag-switch', { 'tag-enable': row.is_ready }]">
            {{ row.is_ready ? $t('启用') : $t('停用') }}
          </span>
        </template>
      </NmColumn>
      <NmColumn prop="colspaOpera" :width="100" :label="$t('操作')" :resizable="false">
        <template #default="{ row }">
          <bk-button v-test="'goDeploy'" text @click="handleOperate(row)">
            {{ row.is_ready ? $t('去部署') : $t('启用插件') }}
          </bk-button>
        </template>
      </NmColumn>
      <bk-table-column
        key="setting"
        prop="colspaSetting"
        :render-header="renderSettingHeader"
        width="42"
        :resizable="false">
      </bk-table-column>

      <NmException
        slot="empty"
        :delay="isLoading"
        :type="tableEmptyType"
        @empty-clear="emptySearchClear()"
        @empty-refresh="emptyRefresh" />
    </bk-table>
  </section>
</template>

<script lang="tsx">
import { Mixins, Component, Prop, Ref, Emit } from 'vue-property-decorator';
import { MainStore, PluginStore } from '@/store';

import { IBkColumn, IPagination, ITabelFliter } from '@/types';
import {  IPluginRow } from '@/types/plugin/plugin-type';
import { CreateElement } from 'vue';
import ColumnSetting from '@/components/common/column-setting.vue';
import HeaderRenderMixin from '@/components/common/header-render-mixins';

@Component({ name: 'plugin-package-table' })
export default class PackageTable extends Mixins(HeaderRenderMixin) {
  @Ref('aliasInput') private readonly aliasInput!: any;
  @Prop({ default: '', type: String }) private readonly searchValue!: string;
  @Prop({ default: () => ([]), type: Array }) private readonly tableList!: IPluginRow[];
  @Prop({ default: () => ({}), type: Object }) private readonly pagination!: IPagination;
  @Prop({ default: true, type: Boolean }) private readonly isLoading!: boolean;
  private get tableData () {
    return this.tableList.map(item => ({
      ...item,
      nodes_number: item.nodes_number || 0,
    }));
  }
  private localMark = 'package_table';
  private filterField = [
    { checked: true, disabled: true, mockChecked: true, name: this.$t('插件别名'), id: 'description' },
    { checked: true, disabled: true, mockChecked: true, name: this.$t('插件名称'), id: 'name' },
    { checked: false, disabled: false, mockChecked: false, name: this.$t('开发商'), id: 'category' },
    { checked: true, disabled: false, mockChecked: true, name: this.$t('已部署节点'), id: 'nodes_number' },
    { checked: false, disabled: false, mockChecked: false, name: this.$t('数据对接SaaS'), id: 'source_app_code' },
    { checked: true, disabled: false, mockChecked: true, name: this.$t('插件描述'), id: 'scenario' },
    { checked: false, disabled: false, mockChecked: false, name: this.$t('部署方式'), id: 'deploy_type' },
    { checked: true, disabled: false, mockChecked: true, name: this.$t('插件状态'), id: 'is_ready' },
  ];

  private get fontSize() {
    return MainStore.fontSize;
  }
  private get tableMaxHeight() {
    return MainStore.windowHeight - 180 - (MainStore.noticeShow ? 40 : 0);
  }
  private get tableEmptyType() {
    return this.searchValue.length ? 'search-empty' : 'empty';
  }

  public async handleOperate(row: IPluginRow) {
    if (row.is_ready) {
      this.$router.push({
        name: 'chooseRule',
        params: {
          defaultPluginId: row.id,
        },
      });
    } else {
      const result = await PluginStore.pluginStatusOperation({ operation: 'ready', id: [row.id] }).catch(() => false);
      if (result) {
        row.is_ready = !row.is_ready;
      }
    }
  }
  public handleViewPlugin(row: IPluginRow) {
    this.$router.push({
      name: 'pluginDetail',
      params: {
        id: row.id,
      },
    });
  }
  public async handleViewTarget(row: IPluginRow) {
    MainStore.setSelectedBiz();
    this.$router.push({
      name: 'plugin',
      params: {
        pluginId: row.id,
        pluginName: row.name,
      },
    });
  }
  public handleGotoSaaS(url: string) {
    window.open(url);
  }

  private handleFieldCheckChange(filter: ITabelFliter[]) {
    this.filterField = JSON.parse(JSON.stringify(filter));
  }
  private renderSettingHeader(h: CreateElement) {
    return h(ColumnSetting, {
      props: {
        localMark: this.localMark,
        value: this.filterField,
        filterHead: true,
      },
      on: {
        update: this.handleFieldCheckChange,
      },
    });
  }
  private getColumnShowStatus(id: string) {
    const item = this.filterField.find(item => item.id === id);
    return !!item?.checked;
  }
  private rowClassName({ row }: {row: IPluginRow }) {
    return row.is_ready ? '' : 'row-disabled';
  }
  private colspanHandle({ column }: { column: IBkColumn}) {
    if (column.property === 'colspaOpera') {
      return [1, 2];
    } if (column.property === 'colspaSetting') {
      return [0, 0];
    }
  }
  @Emit('page-change')
  public handlePageChange(page: number) {
    return page;
  }
  @Emit('limit-change')
  public handleLimitChange(limit: number) {
    return limit;
  }
}
</script>

<style lang="postcss" scoped>
  .plugin-package-table {
    .alias-text-btn {
      display: inline;
      text-overflow: ellipsis;
      overflow: hidden;
      cursor: pointer;
      &:not(.auth-box-diabled) {
        color: #3a84ff;
      }
    }
  }
  .target-preview {
    min-height: 300px;
  }
</style>
