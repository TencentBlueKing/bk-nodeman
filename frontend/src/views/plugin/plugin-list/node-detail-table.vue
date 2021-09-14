<template>
  <section class="node-detail">
    <bk-input
      :placeholder="$t('搜索部署策略')"
      right-icon="bk-icon icon-search"
      ext-cls="node-detail-search"
      clearable
      v-model="searchValue"
      @change="handleValueChange">
    </bk-input>
    <bk-table
      ref="nodeDetailTable"
      :class="`node-detail-table head-customize-table ${ fontSize }`"
      :data="filterData"
      :cell-class-name="handleCellClass">
      <template v-for="key in Object.keys(columnFilter)">
        <bk-table-column
          :key="key"
          :prop="key"
          :resizable="false"
          :label="columnFilter[key].name"
          :fixed="key === 'plugin_name'"
          sortable
          :min-width="columnFilter[key].width || 150"
          show-overflow-tooltip
          v-if="columnFilter[key].mockChecked">
          <template #default="{ row }">
            <!-- 部署方式 -->
            <bk-button
              v-if="columnFilter[key].id === 'deploy_type' && row.system_link"
              text
              @click="handleGotoSaaS(row.system_link)">
              {{ row[columnFilter[key].id] }}
            </bk-button>

            <!-- 自动部署 -->
            <span
              v-else-if="columnFilter[key].id === 'auto_trigger'"
              :class="[{ 'tag-enable': row.auto_trigger, 'tag-switch': row.category === 'policy' }]">
              {{ row.category === 'policy' ? row.auto_trigger ? $t('启用') : $t('停用') : '--' }}
            </span>

            <!-- 状态 -->
            <div class="col-execution" v-else-if="columnFilter[key].id === 'status'">
              <template v-if="row.status">
                <loading-icon class="mr5" v-if="row.status.toLocaleLowerCase() === 'running'"></loading-icon>
                <span :class="`execut-mark execut-${row.status.toLocaleLowerCase()}`" v-else></span>
                <span class="execut-text">{{ statusMap[row.status.toLocaleLowerCase()] | filterEmpty }}</span>
              </template>
              <span v-else>--</span>
            </div>

            <div v-else-if="columnFilter[key].id === 'name'">
              <i class="nodeman-icon nc-sub mr10" v-if="row.parentId"></i>
              <bk-button
                class="button-ellipsis"
                v-if="row.category === 'policy'"
                text
                :disabled="!row[columnFilter[key].id]"
                v-bk-tooltips.right="$t('前往部署策略模块查看')"
                @click="handleGotoRule(row)">
                {{ row[columnFilter[key].id] | filterEmpty }}
              </bk-button>
              <span v-if="row.category === 'once'">{{ $t('手动安装') }}</span>
            </div>

            <div v-else-if="columnFilter[key].id === 'update_time'">
              {{ row.update_time | filterTimezone }}
            </div>

            <template v-else>{{ row[columnFilter[key].id] | filterEmpty }}</template>
          </template>
        </bk-table-column>
      </template>
      <!--自定义字段显示列-->
      <bk-table-column
        key="setting"
        prop="colSetting"
        :render-header="renderHeader"
        fixed="right"
        width="42"
        :resizable="false">
        <template #default="{ row }">
          <div class="operate" v-if="row.category === 'policy'">
            <span class="more-btn" @click="handleShowMore($event, row)">
              <i class="bk-icon icon-more"></i>
            </span>
          </div>
        </template>
      </bk-table-column>
    </bk-table>
    <SelectMenu
      :show="showSelectMenu"
      :target="selectMenuTarget"
      :list="list"
      @on-hidden="showSelectMenu = false"
      @on-select="handleMenuSelect">
    </SelectMenu>
  </section>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { MainStore } from '@/store';
import { IBkColumn } from '@/types';
import ColumnSetting from '@/components/common/column-setting.vue';
import { CreateElement } from 'vue';
import SelectMenu, { IListItem } from '@/components/common/select-menu.vue';

@Component({
  name: 'node-detail-table',
  components: {
    SelectMenu,
  },
})
export default class PluginRuleTable extends Vue {
  @Prop({ default: () => [], type: Array }) private readonly data!: Dictionary[];

  private localMark = 'node_detail_table';
  private searchValue = '';
  private filterData: Dictionary[] = this.data;
  private statusMap = {};
  // 列表字段显示配置
  public columnFilter: Dictionary = {};
  private showSelectMenu = false;
  private list: IListItem[] = [];
  private jobId = -1;
  private selectMenuTarget: HTMLElement | null = null;
  private operateRow: any = null;

  private get fontSize() {
    return MainStore.fontSize;
  }
  private get lastChecked() {
    let lastKey = '';
    Object.keys(this.columnFilter).forEach((key) => {
      if (this.columnFilter[key].mockChecked) {
        lastKey = key;
      }
    });
    return lastKey;
  }

  private created() {
    this.statusMap = {
      pending: window.i18n.t('等待执行'),
      running: window.i18n.t('正在执行'),
      success: window.i18n.t('执行成功'),
      failed: window.i18n.t('执行失败'),
      stop: window.i18n.t('已终止'),
      terminated: window.i18n.t('已终止'),
    };
    this.columnFilter = {
      plugin_name: {
        checked: true,
        disabled: true,
        mockChecked: true,
        name: this.$t('插件名称'),
        id: 'plugin_name',
      },
      name: {
        checked: true,
        disabled: true,
        mockChecked: true,
        name: this.$t('部署策略'),
        id: 'name',
      },
      install_path: {
        checked: false,
        mockChecked: false,
        disabled: false,
        name: this.$t('部署目录'),
        id: 'install_path',
      },
      deploy_type: {
        checked: false,
        mockChecked: false,
        disabled: false,
        name: this.$t('部署方式'),
        id: 'deploy_type',
      },
      auto_trigger: {
        checked: true,
        mockChecked: true,
        disabled: false,
        name: this.$t('自动部署'),
        id: 'auto_trigger',
        width: 100,
      },
      version: {
        checked: true,
        mockChecked: true,
        disabled: false,
        name: this.$t('主程序版本'),
        id: 'version',
        width: 120,
      },
      config_template: {
        checked: false,
        mockChecked: false,
        disabled: false,
        name: this.$t('配置模板'),
        id: 'config_template',
      },
      plugin_version: {
        checked: false,
        mockChecked: false,
        disabled: false,
        name: this.$t('配置模板版本'),
        id: 'plugin_version',
      },
      update_account: {
        checked: false,
        mockChecked: false,
        disabled: false,
        name: this.$t('更新账户'),
        id: 'updated_by',
      },
      status: {
        checked: true,
        mockChecked: true,
        disabled: false,
        name: this.$t('任务状态'),
        id: 'status',
        width: 140,
      },
      update_time: {
        checked: true,
        mockChecked: true,
        disabled: false,
        name: this.$t('最近操作时间'),
        id: 'update_time',
      },
    };
  }

  /**
   * 字段显示列确认事件
   */
  public handleColumnUpdate(data: object) {
    this.columnFilter = data;
    this.$forceUpdate();
  }

  public renderHeader(h: CreateElement) {
    return h(ColumnSetting, {
      props: {
        filterHead: true,
        localMark: this.localMark,
        value: this.columnFilter,
      },
      on: {
        update: this.handleColumnUpdate,
      },
    });
  }
  public handleCellClass({ column, row }: { column: IBkColumn, row: Dictionary }) {
    if (column.property === 'expand' && row.parentId && !row.isLast) {
      return 'row-not-border';
    }
  }
  public handleValueChange(v: string) {
    if (!v.trim()) {
      this.filterData = this.data;
    } else {
      const copyData = JSON.parse(JSON.stringify(this.data));
      this.filterData = copyData.filter((item: Dictionary) => Object.keys(item).some((key) => {
        if (typeof item[key] === 'string') {
          return item[key].includes(v);
        }
        return false;
      }));
    }
  }
  public handleGotoSaaS(url: string) {
    window.open(url);
  }
  public handleGotoRule(row: any) {
    this.$router.push({
      name: 'pluginRule',
      params: {
        name: row.name,
      },
    });
  }
  private handleShowMore(event: Event, row: any) {
    this.list = [
      {
        id: 'MAIN_RELOAD_PLUGIN',
        name: row.job_id ? this.$t('任务详情Item') : this.$t('暂无任务'),
        disabled: !row.job_id,
      },
    ];
    this.jobId = row.job_id;
    this.showSelectMenu = true;
    this.selectMenuTarget = event.target as HTMLElement;
    this.operateRow = row;
  }
  private async handleMenuSelect() {
    this.$router.push({
      name: 'taskDetail',
      params: { taskId: this.jobId },
    });
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-table-body .is-last .cell {
  border-left: unset;
}
.node-detail {
  padding: 30px;
  .node-detail-search {
    width: 500px;
  }
  .node-detail-table {
    margin-top: 14px;
    >>> .row-not-border {
      border-bottom: 0;
    }
    >>> .hide-cell .cell {
      display: none;
    }
    >>> .bk-table-expanded-cell {
      padding: 0 0 0 30px;
      .bk-table-fixed-right {
        border-bottom: 0;
      }
    }
    >>> .is-last .cell {
      border-left: 0;
    }
    .status-success {
      border-color: #e5f6ea;
      background: #3fc06d;
    }
    .status-failed {
      border-color: #ffe6e6;
      background: #ea3636;
    }
    .nc-sub {
      font-size: 16px;
      color: #c4c6cc;
    }
  }
  .operate {
    display: flex;
    align-items: center;
    justify-content: center;
    .more-btn {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      cursor: pointer;
      color: #979ba5;
      font-size: 700;
      margin-right: 2px;
      &:hover {
        color: #3a84ff;
        background: #dcdee5;
      }
    }
  }
}
</style>
