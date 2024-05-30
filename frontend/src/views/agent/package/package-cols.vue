<template>
  <!-- :max-height="windowHeight - 220" -->
  <bk-table
    :class="`pkg-manage-table ${fontSize}`"
    :data="rows"
    :max-height="maxHeight"
    @sort-change="handleSortChange">
    <NmColumn :label="$t('包名称')" prop="pkg_name" min-width="210" fixed />
    <NmColumn
      key="version"
      v-if="filter['version'].mockChecked"
      :label="$t('版本号')"
      prop="version"
      min-width="120"
      :render-header="renderFilterHeader"
      sortable="custom"/>
    <NmColumn
      key="os_cpu_arch"
      v-if="filter['os_cpu_arch'].mockChecked"
      :label="$t('操作系统/架构')"
      prop="os_cpu_arch"
      min-width="120"
      :render-header="renderFilterHeader">
      <template #default="{ row }">
        {{ `${row.os}_${row.cpu_arch}` }}
      </template>
    </NmColumn>
    <NmColumn
      key="tag_names"
      :label="$t('标签信息')"
      prop="tag_names"
      min-width="200"
      :show-overflow-tooltip="false"
      :render-header="renderFilterHeader"
      class-name="edit-tag-column">
      <template #default="{ row }">
        <edit-tag
          :key="row.id"
          field="tags"
          @editTag="(val) => handleEditTags(row, val)"
          :options="options"
          :value="row.formatTags" />
      </template>
    </NmColumn>
    <NmColumn
      key="created_by"
      :label="$t('上传用户')"
      prop="created_by"
      min-width="120"
      :render-header="renderFilterHeader" />
    <NmColumn
      key="created_time"
      v-if="filter['created_time'].mockChecked"
      :label="$t('上传时间')"
      prop="created_time"
      class-name="config-cell"
      min-width="150"
      sortable />
    <NmColumn
      key="hostNumber"
      v-if="filter['hostNumber'].mockChecked"
      :label="$t('已部署主机')"
      prop="hostNumber"
      min-width="120"
      align="right"
      sortable>
      <template #default="{ row }">
        <span v-if="row.hostNumber" class="nm-link" @click="goAgentStatus(row)">{{ row.hostNumber }}</span>
        <span v-else>0</span>
      </template>
    </NmColumn>
    <NmColumn
      key="is_ready"
      v-if="filter['is_ready'].mockChecked"
      :label="$t('状态')"
      prop="is_ready"
      min-width="90"
      align="center"
      :render-header="renderFilterHeader">
      <template #default="{ row }">
        <span :class="['tag-switch', { 'tag-enable': row.is_ready }]">
          {{ row.is_ready ? $t('启用') : $t('停用')}}
        </span>
      </template>
    </NmColumn>
    <NmColumn key="message" :label="$t('操作')" prop="message" min-width="100" fixed="right">
      <template #default="{ row }">
        <bk-button v-if="!row.is_ready" text theme="primary" :disabled="btnLoading[row.id]" @click="switchPkgStatus(row)">
          {{ $t('启用')}}
        </bk-button>
        <bk-popconfirm
          width="320"
          trigger="click"
          :confirm-text="$t('停用')"
          @confirm="switchPkgStatus(row)">
          <div slot="content">
            <div class="title">{{ $t('确认停用该Agent包') }}</div>
            <p>{{ $t('确认停用该Agent包Tip1', [row.pkg_name]) }}</p>
            <p>{{ $t('确认停用该Agent包Tip2') }}</p>
          </div>
          <bk-button v-if="row.is_ready" text theme="primary" :disabled="btnLoading[row.id]">
            {{ $t('停用') }}
          </bk-button>
        </bk-popconfirm>
        <bk-popconfirm
          width="320"
          trigger="click"
          :confirm-text="$t('删除')"
          @confirm="detelePkg(row)">
          <div slot="content">
            <div class="title">{{ $t('确认删除该Agent包') }}</div>
            <p>{{ $t('确认删除该Agent包Tip1', [row.pkg_name]) }}</p>
            <p>{{ $t('确认删除该Agent包Tip2') }}</p>
          </div>
          <bk-button
            v-if="!row.is_ready"
            class="ml10"
            text
            theme="primary"
            :disabled="btnLoading[row.id]">
            {{ $t('删除') }}
          </bk-button>
        </bk-popconfirm>
      </template>
    </NmColumn>
    <!--表格设置-->
    <NmColumn
      key="setting"
      prop="colspaSetting"
      :render-header="renderHeader"
      width="42"
      :resizable="false"
      fixed="right">
    </NmColumn>
  </bk-table>
</template>
<script lang="ts">
import { Mixins, Emit, Component, Prop, Watch } from 'vue-property-decorator';
import i18n from '@/setup';
import { AgentStore } from '@/store';
import ColumnSetting from '@/components/common/column-setting.vue';
import { ISearchItem, ITabelFliter } from '@/types';
import { PropType, defineComponent, getCurrentInstance, reactive, toRefs, CreateElement } from 'vue';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import { IPkgRow } from '@/types/agent/pkg-manage';
import HeaderRenderMixin from '@/components/common/header-render-mixins';
import EditTag from '@/components/common/tag.vue';
import { MainStore } from '@/store/index';

@Component({
  components: {
    FlexibleTag,
    EditTag,
  },
})
export default class PackageCols extends Mixins(HeaderRenderMixin) {
  @Prop({ type: Array, default: () => [] }) rows!: IPkgRow[];
  @Prop({ type: Number, default: 0 }) maxHeight!: number;
  @Prop({ type: Array, default: () => [] }) options!: ISearchItem[];
  @Prop({ default: () => ([]), type: Array }) private readonly searchSelectData!: ISearchItem[];

  @Watch('searchSelectData', { deep: true, immediate: true })
  private handleSearchSelectDataChange(data: ISearchItem[]) {
    this.filterData = JSON.parse(JSON.stringify(data));
  }
  
  private created() {
    this.filterData.splice(0, this.filterData.length, ...JSON.parse(JSON.stringify(this.searchSelectData)));
  }

  filter = reactive<{ [key: string]: ITabelFliter }>({
    pkg_name: {
      checked: true,
      disabled: true,
      mockChecked: true,
      name: window.i18n.t('包名称'),
      id: 'pkg_name',
    },
    version: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('版本号'),
      id: 'version',
    },
    os_cpu_arch: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('操作系统/架构'),
      id: 'os_cpu_arch',
    },
    tag_names: {
      checked: true,
      disabled: true,
      mockChecked: true,
      name: window.i18n.t('标签信息'),
      id: 'tag_names',
    },
    created_by: {
      checked: true,
      disabled: true,
      mockChecked: true,
      name: window.i18n.t('上传用户'),
      id: 'created_by',
    },
    created_time: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('上传时间'),
      id: 'created_time',
    },
    hostNumber: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('已部署主机'),
      id: 'hostNumber',
    },
    is_ready: {
      checked: true,
      disabled: false,
      mockChecked: true,
      name: window.i18n.t('状态'),
      id: 'is_ready',
    },
  });

  activeRow = reactive<Pick<IPkgRow, 'id' | 'is_ready'>>({
    id: -1,
    is_ready: false,
  });

  btnLoading = reactive<{ [id: string]: boolean }>({});

  get localMark() {
    return 'agent_package';
  }

  private get fontSize() {
    return MainStore.fontSize;
  }

  renderHeader(h: CreateElement) {
    return h(ColumnSetting, {
      props: {
        'filter-head': true,
        localMark: this.localMark,
        value: this.filter,
      },
      on: {
        update: (data: { [key: string]: ITabelFliter }) => this.handleColumnUpdate(data),
      },
    });
  }

  @Emit('pagetion')
  async handleEditTags(row: IPkgRow, tags: string[]) {
    // 给表格对应行数据设置标签
    await AgentStore.apiPkgUpdateStatus({ id: row.id, is_ready: row.is_ready, tags });
  }

  handleColumnUpdate(data: { [key: string]: ITabelFliter }) {
    Object.assign(this.filter, data);
  }

  @Emit('orderChange')
  handleEmitOrderSort({ prop, ordering }: { prop: string, ordering: string }) {
    return ordering;
  }
  handleSortChange({ prop, order }: { prop: string, order: string }) {
    if (prop === 'version') {
      const ordering = order === 'ascending' ? 'version' : '-version';
      this.handleEmitOrderSort({ prop, ordering });
    }
  }

  async switchPkgStatus(row: IPkgRow) {
    this.activeRow = row;
    const isReady = !this.activeRow.is_ready;
    const res = await AgentStore.apiPkgUpdateStatus({ id: this.activeRow.id, is_ready: isReady });
    if (res?.id) {
      this.activeRow.is_ready = isReady;
      this.$bkMessage({
        theme: 'success',
        message: isReady ? window.i18n.t('启用成功') : window.i18n.t('停用成功'),
      });
      this.$forceUpdate();
    }
  }
  @Emit('pagetion')
  async detelePkg(row: IPkgRow) {
    this.activeRow = row;
    const res = await AgentStore.apiPkgDelete(this.activeRow.id);
    if (res) {
      this.$bkMessage({
        theme: 'success',
        message: window.i18n.t('删除成功'),
      });
      this.$forceUpdate();
      return;
    }
  }


  goAgentStatus(row: IPkgRow) {
    this.$router.push({
      name: 'agentStatus',
      params: {
        os_type: row.os,
        version: row.version,
      },
    });
  }
};
</script>
<style lang="postcss">
@import "@/css/variable.css";
.edit-tag-column {
  .cell {
    overflow: initial;
    line-height: 18px;
    text-overflow: initial;
    word-break: break-all;
    -webkit-line-clamp: unset;

    .edit-tag {
      margin-left: -4px;
    }
  }
}
.pkg-manage-table {
  .flexible-tag-group .tag-item {
    &.stable {
      color: #14a568;
      background-color: #e4faf0;
    }
    &.latest {
      color: $primaryFontColor;
      background-color: #edf4ff;
    }
    &.test {
      color: #fe9c00;
      background-color: #fff1db;
    }
  }
}
.bk-popconfirm-content.popconfirm-more  {
  .popconfirm-content {
    .title {
      font-size: 16px;
      color: #313238;
      letter-spacing: 0;
      line-height: 24px;
      padding-bottom: 10px;
    }
    p {
      color: #63656E;
      padding-bottom: 5px;
    }
  }
  .popconfirm-operate {
    padding-top: 18px;
    .default-operate-button {
      width: 64px;
      margin-left: 8px;
    }
  }
}

</style>
