<template>
  <section>
    <bk-table
      v-test.policy="'policyTable'"
      ref="tableRef"
      :data="sortTableData"
      :pagination="pagination"
      :max-height="windowHeight - 315"
      :row-class-name="rowClassName"
      @row-click="handleRowClick">
      <bk-table-column class-name="td-radio" :width="50" prop="value" :resizable="false">
        <template #default="{ row }">
          <bk-radio
            v-test.policy="'policyRadio'"
            :value="chooseId === row.id"
            v-authority="{
              active: !row.permissions || !row.permissions.edit,
              apply_info: getRowOperateAuthInfo(row)
            }"></bk-radio>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('策略名称')"
        prop="name"
        :render-header="renderHeader">
      </bk-table-column>
      <bk-table-column :label="$t('最近修改人')" prop="creator" sortable></bk-table-column>
      <bk-table-column :label="$t('最近部署时间')" prop="update_time" sortable>
        <template #default="{ row }">
          {{ row.update_time | filterTimezone }}
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('关联主机数')">
        <template #default="{ row }">
          <span :class="{ num: !!row.associated_host_num }" @click.stop="handleViewTarget(row)">
            {{ row.associated_host_num || 0 }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('包含业务')">
        <template #default="{ row }">
          <span v-if="row.bk_biz_scope">{{ getRowBizText(row) }}</span>
          <span v-else>--</span>
        </template>
      </bk-table-column>
    </bk-table>
    <bk-dialog
      width="1000"
      ext-cls="target-preview-dialog"
      v-model="showPreview"
      :mask-close="false"
      :draggable="false"
      :header-position="'left'"
      :title="$t('关联主机预览')"
      :show-footer="false">
      <div class="target-preview">
        <NodePreview
          v-if="showPreview"
          :active="targetType"
          :get-table-list="getTargetTable"
          :collapse-list="[{ name: 'host', com: 'staticContentTable', path: '已关联主机' }]">
        </NodePreview>
      </div>
    </bk-dialog>
  </section>
</template>
<script lang="ts">
import { Component, Vue, Ref, Prop, Emit } from 'vue-property-decorator';
import { CreateElement } from 'vue';
import FilterFunnel from '../components/filter-funnel.vue';
import SortCaret from '../components/sort-caret.vue';
import NodePreview from '@/components/ip-select-nm/node-preview.vue';
import { MainStore, PluginStore } from '@/store';
import { IPolicyBase } from '@/types/plugin/plugin-type';
import { IBkColumn } from '@/types';
import { bus } from '@/common/bus';

@Component({
  name: 'rule-table',
  components: {
    NodePreview,
  },
})
export default class RuleTable extends Vue {
  @Ref('tableRef') private readonly tableRef!: any;
  @Prop({ type: Array, default: () => ([]) }) private readonly tableData!: IPolicyBase[];
  @Prop({ type: [String, Number], default: '' }) private readonly chooseId: string | number = '';

  private searchRuleName = '';
  private pagination = {
    current: 0,
    count: 0,
    limit: 20,
  };
  private sort = 'normal';
  private showPreview = false;
  private currentRow: IPolicyBase | null = null;
  private targetType: 'TOPO' | 'HOST' = 'TOPO';

  private get sortTableData() {
    const data = this.tableData.slice(0);
    const searchArr = this.searchRuleName.split('|');
    return data.sort(() => {
      if (this.sort === 'normal') {
        return 0;
      }
      return this.sort === 'desc' ? -1 : 1;
    }).filter(item => item.name && (searchArr.length > 1
      ? searchArr.some(key => item.name.includes(key)) : item.name.indexOf(this.searchRuleName) > -1));
  }
  private get windowHeight() {
    return MainStore.windowHeight;
  }

  @Emit('rule-choose')
  public handleRowChoose(id: number) {
    return id;
  }
  public handleRowClick(row: IPolicyBase) {
    if (row.permissions && row.permissions.edit) {
      this.handleRowChoose(row.id);
    } else {
      bus.$emit('show-permission-modal', {
        params: {
          apply_info: this.getRowOperateAuthInfo(row),
        },
      });
    }
  }

  public renderHeader(h: CreateElement, { column }: { column: IBkColumn }) {
    return h(
      'span',
      {
        class: 'filter-label',
        on: {
          click: this.handleFilterLabelClick,
        },
      },
      [
        column.label,
        h(SortCaret, {
          on: {
            'sort-change': this.handleSortChange,
          },
          ref: 'sortcaret',
        }),
        h(
          FilterFunnel,
          {
            props: {
              data: this.searchRuleName,
            },
            on: {
              confirm: this.filterConfirm,
              reset: this.filterReset,
            },
          },
        ),
      ],
    );
  }
  public handleFilterLabelClick() {
    try {
      this.tableRef.$refs.tableHeader.$refs.sortcaret.changeSort();
    } catch {
      console.error('get sortcaret ref error');
    }
  }
  public handleSortChange(sort: 'normal' | 'desc' | 'asc') {
    this.sort = sort;
  }

  public filterConfirm(name: string) {
    this.searchRuleName = name;
  }

  public filterReset() {
    this.searchRuleName = '';
  }
  public getRowBizText(row: IPolicyBase) {
    if (row.bk_biz_scope && row.bk_biz_scope.length) {
      return row.bk_biz_scope.map((item: { 'bk_biz_name': string }) => item.bk_biz_name).join('/');
    }
    return '--';
  }
  public async handleViewTarget(row: IPolicyBase) {
    if (row.associated_host_num) {
      this.currentRow = row;
      this.showPreview = true;
      this.targetType = 'HOST';
    }
  }
  public async getTargetTable(params: any) {
    params.name = this.currentRow?.name;
    params.policy_id = this.currentRow?.id;
    params.with_hosts = this.targetType === 'HOST';
    const { list, total, nodes = [] } = await PluginStore.getTargetPreview(params);
    let nodesList = nodes;
    if (this.targetType !== 'HOST') {
      nodesList = await PluginStore.getNodesAgentStatus({ page: 1, pagesize: -1, nodes });
    }
    return {
      list: this.targetType === 'HOST' ? list : nodesList,
      total: this.targetType === 'HOST' ? total : nodesList.length,
    };
  }
  private rowClassName({ row }: {row: IPolicyBase }) {
    return row.permissions && row.permissions.edit ? '' : 'row-disabled';
  }
  private getRowOperateAuthInfo(row: IPolicyBase) {
    if (row.permissions && row.permissions.edit) {
      return [];
    }
    const info = [
      { action: 'strategy_operate', instance_id: row.id, instance_name: row.name },
    ];
    if (row.bk_biz_scope && row.bk_biz_scope.length) {
      row.bk_biz_scope.forEach((item) => {
        info.push({
          action: 'strategy_create',
          instance_id: item.bk_biz_id,
          instance_name: item.bk_biz_name,
        });
      });
    }
    return info;
  }
}
</script>
<style lang="postcss" scoped>
.num {
  cursor: pointer;
  color: #3a84ff;
}
>>> .filter-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}
>>> .bk-table-row {
  cursor: pointer;
  &.row-disabled {
    cursor: default;
  }
}
>>> .td-radio {
  input[type=radio] {
    margin: 0;
  }
}
</style>
