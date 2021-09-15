<template>
  <bk-dialog
    :value="value"
    width="960"
    :position="{ top: 100 }"
    :draggable="false"
    :title="$t('选择部署版本')"
    header-position="left"
    @cancel="handleCancel">
    <div class="detail-table" v-bkloading="{ isLoading: loading }">
      <bk-table
        :data="data"
        class="detail-table-left"
        v-test.policy="'chooseVersionTable'"
        :row-class-name="handleRowClass"
        @row-click="handleRowClick">
        <bk-table-column width="60" align="center">
          <template #default="{ row }">
            <bk-radio v-test.policy="'versionRadio'" :disabled="row.disabled"
                      :value="selectedVersion === row.version"
                      width="90"
                      v-bk-tooltips.left="{
                        content: row.isBelowVersion ? $t('版本未处于正式状态') : $t('不能低于当前版本'),
                        disabled: !row.disabled
                      }">
            </bk-radio>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('插件包版本')" sortable prop="version">
          <template #default="{ row, $index }">
            <span>{{ row.version | filterEmpty }}</span>
            <!-- 测试用例 -->
            <bk-popover v-if="$index < 2 && !row.is_newest" placement="right-start">
              <span v-if="row.is_release_version === false" class="tag-switch tag-yellow ml5">{{ $t('测试') }}</span>
              <div slot="content">
                <p>{{ $t('测试版本提示line1') }}</p>
                <p>{{ $t('测试版本提示line2') }}</p>
              </div>
            </bk-popover>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('已部署数')" prop="nodes_number" align="right" sortable>
          <template #default="{ row }">
            <span class="num-link">{{ row.nodes_number || 0 }}</span>
          </template>
        </bk-table-column>
        <bk-table-column width="40" resizable>
          <template #default="{ row }">
            <i class="bk-icon icon-right-shape active-arrow" v-show="selectedVersion === row.version"></i>
          </template>
        </bk-table-column>
      </bk-table>
      <div class="detail-table-right">
        <p class="title">{{ $t('版本描述') }}</p>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="markdown-body" v-html="markdown"></div>
      </div>
    </div>
    <template slot="footer">
      <bk-button theme="primary" :disabled="!selectedVersion" @click="handleConfirm">{{ $t('确定') }}</bk-button>
      <bk-button class="ml10" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </template>
  </bk-dialog>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Model, Watch } from 'vue-property-decorator';
import { IPkVersionRow } from '@/types/plugin/plugin-type';

@Component({
  name: 'version-detail-table',
})
export default class VersionDetailTable extends Vue {
  @Model('change', { default: false, type: Boolean }) private readonly value!: boolean;
  @Prop({ type: Array, default: () => ([]) }) private readonly data!: IPkVersionRow[];
  @Prop({ default: false, type: Boolean }) private readonly loading!: boolean;
  @Prop({ type: String, default: '' }) private readonly version!: string;

  private selectedVersion = '';
  private selectedRow: IPkVersionRow | null = null;
  private markdown = '';

  @Watch('loading')
  public handleShow(val: boolean) {
    if (val) {
      this.selectedRow = null;
    } else {
      this.selectedVersion = this.version;
      this.selectedRow = this.data.find(row => row.version === this.version) || null;
    }
  }

  @Emit('target-change')
  public handleConfirm() {
    return this.selectedRow;
  }
  @Emit('change')
  public handleCancel() {
    this.selectedRow = null;
    return false;
  }

  public handleRowClass({ row }: {row: IPkVersionRow}) {
    if (row.disabled) {
      return 'row-disabled';
    }
    if (row.version === this.selectedVersion) {
      return 'row-active';
    }
  }

  public handleRowClick(row: IPkVersionRow) {
    if (!row.disabled) {
      this.selectedRow = row;
      this.selectedVersion = row.version as string;
    }
  }
  public async handleViewTarget() {
    this.$router.push({ name: 'plugin' });
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-table-body {
  tr {
    cursor: pointer;
    &.row-disabled {
      cursor: not-allowed;
    }
  }
  tr:hover {
    /* stylelint-disable-next-line declaration-no-important */
    background-color: #f0f1f5 !important;
  }
  tr:hover>td {
    /* stylelint-disable-next-line declaration-no-important */
    background-color: #f0f1f5 !important;
  }
  .row-active {
    background-color: #f0f1f5;
    .tag-enable {
      background: #d6e7da;
    }
  }
  td.is-last .cell {
    padding: 0;
  }
  .tag-yellow {
    height: 18px;
    line-height: 18px;
  }
}
.detail-table {
  height: 100%;
  display: flex;
  >>> .bk-table-header {
    th {
      background-color: #fafbfd;
    }
  }
  &-left {
    flex: 1;
    flex-basis: 340px;
    .active-arrow {
      color: #979ba5;
    }
  }
  &-right {
    flex-basis: 620px;
    border: 1px solid #dcdee5;
    display: flex;
    flex-direction: column;
    border-left: 0;
    z-index: 0;
    .title {
      height: 43px;
      line-height: 43px;
      padding-left: 22px;
      background: #fafbfd;
      border-bottom: 1px solid #dcdee5;
      font-size: 12px;
      color: #313238;
    }
    .content {
      border: 0;
      height: 100%;
    }
  }
}
</style>
