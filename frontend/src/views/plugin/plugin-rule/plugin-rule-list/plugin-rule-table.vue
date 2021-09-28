<template>
  <section>
    <bk-table
      v-test="'policyTable'"
      :class="`head-customize-table ${ fontSize }`"
      :data="data"
      :max-height="windowHeight - 180"
      :pagination="pagination"
      :row-class-name="rowClassName"
      :span-method="colspanHandle"
      :cell-class-name="handleCellClass"
      @row-mouse-enter="handleRowEnter"
      @row-mouse-leave="handleRowLeave"
      @page-change="handlePageChange"
      @page-limit-change="handleLimitChange"
      @row-click="handleRowClick"
      @expand-change="handleExpandChange">
      <bk-table-column width="36" prop="expand" :resizable="false" fixed>
        <template #default="{ row }">
          <div
            v-if="row.hasGrayRule"
            :class="['bk-table-expand-icon', { 'bk-table-expand-icon-expanded': row.expand }]">
            <i class="bk-icon icon-play-shape"></i>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column width="12" :resizable="false" class-name="abnormal-column" fixed>
        <template #default="{ row }">
          <bk-popover
            v-if="row.abnormal_host_count && row.enable"
            placement="top-start"
            theme="light"
            :tippy-options="{ boundary: 'window' }">
            <i class="nodeman-icon nc-alert warn"></i>
            <div class="policy-tip-content" slot="content">
              <i18n path="当前策略下有主机安装插件失败"><b class="error">{{ row.abnormal_host_count }}</b></i18n>
              <p>{{ $t('且已超过最大尝试次数') }}</p>
              <i18n path="如需再次尝试安装请点击重试失败">
                <bk-button :text="true" title="primary" @click="handleRuleOperate(row, 'RETRY_ABNORMAL')">
                  {{ $t('失败重试') }}
                </bk-button>
              </i18n>
            </div>
          </bk-popover>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('部署策略')" min-width="200" class-name="name-column" label-class-name="name-column" fixed>
        <template #default="{ row }">
          <bk-input
            v-if="editId === row.id"
            ref="nameInput"
            v-model="editName"
            @blur="handleBlur(row)"
            @enter="handleEnter">
          </bk-input>
          <div class="plugin-rule-name" v-else>
            <span class="gray-tag text-gray mr4" v-if="row.isGrayRule">[{{ $t('灰度') }}]</span>
            <span class="alias-text-btn">{{ row.name }}</span>
            <i
              v-show="hoverId === row.id"
              v-authority="{
                active: !row.permissions || !row.permissions.edit,
                apply_info: [{
                  action: 'strategy_operate',
                  instance_id: row.id,
                  instance_name: row.name
                }]
              }"
              class="ml5 nodeman-icon nc-icon-edit-2"
              @click.stop="handleEdit(row)">
            </i>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('插件名称')" prop="plugin_name" min-width="140">
        <template #default="{ row }">
          <span>{{ row.plugin_name | filterEmpty }}</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('策略状态')" prop="enable" min-width="100" :render-header="renderFilterHeader">
        <template #default="{ row }">
          <span v-if="!row.isGrayRule" :class="['tag-switch', { 'tag-enable': row.enable }]">
            {{ row.enable ? $t('启用') : $t('停用') }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column v-if="filter['host_num'].mockChecked" :label="$t('关联主机数')" align="right" width="90">
        <template #default="{ row }">
          <div class="num-link">
            <span class="num" v-test="'filterNode'" @click.stop="handleViewAssociatedHost(row)">
              {{ row.associated_host_num || 0 }}
            </span>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column v-if="filter['host_num'].mockChecked" min-width="40" :resizable="false"></bk-table-column>
      <bk-table-column v-if="filter['biz_scope'].mockChecked" :label="$t('包含业务')" min-width="140">
        <template #default="{ row, $index }">
          <FlexibleTag
            :ref="`flexibleTagRef${$index}`"
            v-if="row.bk_biz_scope && row.bk_biz_scope.length"
            id-key="bk_biz_name"
            :list="row.bk_biz_scope">
          </FlexibleTag>
          <span v-else>--</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('部署版本')" key="configs" min-width="170">
        <div slot-scope="{ row, $index }" class="col-execution">
          <div class="execut-text" v-if="row.configs">
            <p v-for="config in row.configs" :key="`${$index}_${config.os}`">
              <i :class="`large td-sys-icon nodeman-icon nc-${config.os}`"></i>
              {{ config.cpu_arch }}:
              <span
                :class="{
                  warn: config.compare_with_root === -1,
                  success: config.compare_with_root === 1
                }">{{ config.version }}</span>
            </p>
          </div>
          <span v-else>--</span>
        </div>
      </bk-table-column>
      <bk-table-column v-if="filter['creator'].mockChecked" :label="$t('操作账号')" prop="creator" min-width="120" />
      <bk-table-column
        v-if="filter['update_time'].mockChecked"
        :label="$t('最近操作时间')"
        prop="update_time"
        min-width="180">
        <template #default="{ row }">
          {{ row.update_time | filterTimezone }}
        </template>
      </bk-table-column>
      <bk-table-column prop="colspanOperate" :label="$t('操作')" width="150" :resizable="false">
        <template #default="{ row }">
          <template v-if="row.id === deleteId">
            <loading-icon class="mr5"></loading-icon>
            <span>{{ $t('正在删除') }}</span>
          </template>
          <bk-button
            v-else-if="['PENDING', 'RUNNING'].includes(row.job_result.status)"
            text
            @click.stop="handleGotoTask(row)">
            <loading-icon></loading-icon>
            <span class="loading-name" v-bk-tooltips.top="$t('查看任务详情')">
              {{ `${row.status === 'PENDING' ? $t('等待') : $t('正在')} ${row.job_result.op_type_display}` }}
            </span>
          </bk-button>
          <div v-else class="operate" v-authority="{
            active: !row.permissions || !row.permissions.edit,
            apply_info: getRowOperateAuthInfo(row)
          }">
            <!-- 灰度策略 -->
            <template v-if="row.isGrayRule">
              <!-- 主策略停用后，灰度策略的【发布】和【编辑】都禁用掉，只保留【删除】 -->
              <bk-button
                v-test="'editGray'" text :disabled="!row.enable" @click.stop="handleRuleOperate(row, 'editGray')">
                {{ $t('编辑') }}
              </bk-button>
              <bk-button v-test="'releaseGray'" text class="ml10"
                         :disabled="!row.enable"
                         v-bk-tooltips.top="{
                           width: 200,
                           content: $t('灰度发布btn提示', [row.plugin_name])
                         }"
                         @click.stop="handleRuleOperate(row, 'releaseGray')">
                {{ $t('发布') }}
              </bk-button>
              <bk-button v-test="'deleteGray'" text class="ml10"
                         v-bk-tooltips.bottom-end="{
                           width: 200,
                           content: $t('灰度删除btn提示', [row.plugin_name])
                         }"
                         @click.stop="handleRuleOperate(row, 'deleteGray')">
                {{ $t('删除') }}
              </bk-button>
            </template>
            <!-- 主策略 - 启用 -->
            <template v-else-if="row.enable">
              <bk-button v-test="'edit'" text @click.stop="handleRuleOperate(row, 'edit')">{{ $t('编辑') }}</bk-button>
              <bk-popover placement="top">
                <bk-button v-test="'createGray'" text class="ml10" @click.stop="handleRuleOperate(row, 'createGray')">
                  {{ $t('灰度') }}
                </bk-button>
                <i18n path="多行国际化" slot="content">
                  <p>{{ $t('新建灰度策Tip') }}</p>
                  <p>{{ $t('主策略版本保持不变Tip') }}</p>
                </i18n>
              </bk-popover>
              <bk-button v-test="'stop'" text class="ml10" @click.stop="handleRuleOperate(row, 'stop')">
                {{ $t('停用') }}
              </bk-button>
            </template>
            <!-- 主策略 - 停用: 可存在灰度策略, 无新增灰度入口, 不可发布、编辑灰度, 可删除灰度 -->
            <template v-else>
              <bk-button v-test="'start'" text @click.stop="handleRuleOperate(row, 'start')">
                {{ $t('启用') }}
              </bk-button>
              <bk-button v-if="!row.associated_host_num" text class="ml10" @click.stop.prevent>
                <bk-popconfirm
                  v-test="'delete'"
                  trigger="click"
                  width="280"
                  :title="$t('是否删除此策略')"
                  :content="$t('删除操作无法撤回请谨慎操作')"
                  @confirm="handleRuleOperate(row, 'delete')">
                  {{ $t('删除') }}
                </bk-popconfirm>
              </bk-button>
              <bk-button v-test="'stopAndDelete'"
                         v-else text class="ml10" @click.stop="handleRuleOperate(row, 'stop_and_delete')">
                {{ $t('卸载并删除') }}
              </bk-button>
            </template>
          </div>
        </template>
      </bk-table-column>
      <!--自定义字段显示列-->
      <bk-table-column
        key="setting"
        prop="colspanSetting"
        :render-header="renderHeader"
        width="42"
        :resizable="false">
        <template #default="{ row }">
          <div class="operate">
            <span class="more-btn" @click="handleShowMore($event, row)">
              <i class="bk-icon icon-more"></i>
            </span>
          </div>
        </template>
      </bk-table-column>
    </bk-table>
  </section>
</template>
<script lang="ts">
import { Component, Ref, Prop, Emit, Mixins } from 'vue-property-decorator';
import { IPolicyRow } from '@/types/plugin/plugin-type';
import { IBkColumn, IPagination, ISearchItem, ITabelFliter } from '@/types';
import { MainStore, PluginStore } from '@/store';
import HeaderRenderMixin from '@/components/common/header-render-mixins';
import { debounceDecorate } from '@/common/util';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import ColumnSetting from '@/components/common/column-setting.vue';
import { CreateElement } from 'vue/types/umd';

type GrayType = 'createGray' | 'editGray' | 'deleteGray' | 'releaseGray';
type PolicyType = 'edit' | 'start' | 'stop' | 'delete' | 'stop_and_delete' | 'RETRY_ABNORMAL';

@Component({
  name: 'plugin-rule-table',
  components: {
    FlexibleTag,
  },
})
export default class PluginRuleTable extends Mixins(HeaderRenderMixin) {
  @Ref('nameInput') private readonly nameInput: any;

  @Prop({ type: Array, default: () => ({}) }) private readonly data!: IPolicyRow[];
  @Prop({ type: Number, default: -1 }) private readonly deleteId!: number;
  @Prop({ type: Object, default: () => ({
    current: 1,
    count: 0,
    limit: 20,
  }) }) private readonly pagination!: IPagination;
  @Prop({ default: () => ([]), type: Array }) public readonly filterList!: ISearchItem[];

  private editId: number | string = '';
  private editName = '';
  private hoverId: number | string = '';
  public filterData: ISearchItem[] = this.filterList;
  private localMark = '__rule_list_table__';
  private filter: { [key: string]: ITabelFliter } = {
    name: { checked: true, disabled: true, mockChecked: true, name: window.i18n.t('部署策略'), id: 'name' },
    plugin_name: { checked: true, disabled: true, mockChecked: true, name: window.i18n.t('插件名称'), id: 'name' },
    enable: { checked: true, disabled: true, mockChecked: true, name: window.i18n.t('策略状态'), id: 'name' },
    host_num: { checked: true, disabled: false, mockChecked: true, name: window.i18n.t('关联主机数'), id: 'host_num' },
    biz_scope: { checked: true, disabled: false, mockChecked: true, name: window.i18n.t('包含业务'), id: 'biz_scope' },
    version: { checked: true, disabled: true, mockChecked: true, name: window.i18n.t('部署版本'), id: 'name' },
    creator: { checked: true, disabled: false, mockChecked: true, name: window.i18n.t('操作账号'), id: 'creator' },
    update_time: { checked: true, disabled: false, mockChecked: true, name: window.i18n.t('最近操作时间'), id: 'update_time' },
  };

  private get bkBizList() {
    return MainStore.bkBizList;
  }
  private get windowHeight() {
    return MainStore.windowHeight;
  }
  private get language() {
    return MainStore.language;
  }
  private get fontSize() {
    return MainStore.fontSize;
  }

  private mounted() {
    window.addEventListener('resize', this.reCalcFlexibleTag);
  }
  private beforeDestroy() {
    window.removeEventListener('resize', this.reCalcFlexibleTag);
  }

  @Emit('page-change')
  private handlePageChange(newPage: number) {
    return newPage;
  }
  @Emit('limit-change')
  private handleLimitChange(limit: number) {
    return limit;
  }

  @Emit('more-operate')
  private moreOperate(row: IPolicyRow, type: string) {
    return { row, type };
  }
  @Emit('expand-change')
  private handleExpandChange(row: IPolicyRow) {
    return row;
  }

  private handleRuleOperate(row: IPolicyRow, type: GrayType | PolicyType) {
    if (['delete', 'stop'].includes(type)) {
      this.moreOperate(row, type);
    } else {
      // edit start stop_and_delete RETRY_ABNORMAL
      // createGray, editGray, deleteGray releaseGray, RETRY_ABNORMAL
      const params: Dictionary = {
        type,
        id: row.id,
        policyName: row.name || '',
        pluginId: row.plugin_id,
        pluginName: row.plugin_name,
      };
      if (type === 'releaseGray') {
        params.id = row.pid; // 灰度发布 - 使用的主策略id发布
        params.subId = row.id;
      }
      if (type === 'RETRY_ABNORMAL') { // 策略失败主机重试
        params.bkHostId = row.abnormal_host_ids;
      }
      this.$router.push({ name: 'createRule', params });
    }
  }

  private handleRowClick(row: IPolicyRow) {
    if (row.hasGrayRule) {
      this.handleExpandChange(row);
    }
  }

  private handleEdit(row: IPolicyRow) {
    this.editId = row.id;
    this.editName = row.name;
    this.$nextTick(() => {
      this.nameInput && this.nameInput.focus();
    });
  }

  private async handleBlur(row: IPolicyRow) {
    const valueTrim = this.editName.trim();
    this.editId = '';
    this.editName = '';
    if (valueTrim === '' || valueTrim === row.name) return;
    const message = this.verifyAlias(valueTrim);
    if (message) {
      this.$bkMessage({
        theme: 'error',
        message,
      });
      return;
    }
    const res = await PluginStore.updatePolicyInfo({ pk: row.id, params: { name: valueTrim } });
    if (res) {
      this.$bkMessage({
        theme: 'success',
        message: this.$t('修改成功'),
      });
      row.name = valueTrim;
    }
  }
  private async handleEnter() {
    this.nameInput && this.nameInput.blur();
  }
  public verifyAlias(value: string) {
    let message;
    const valueLength = value.replace(/[\u0391-\uFFE5]/g, 'aa').length;
    if (valueLength > 40) {
      message = this.$t('长度不能大于20个中文或40个英文字母');
    }
    return message;
  }

  private handleRowEnter(index: number, event: Event, row: IPolicyRow) {
    this.hoverId = row.id;
  }

  private handleRowLeave() {
    this.hoverId = '';
  }

  // 查看关联的主机
  public async handleViewAssociatedHost(row: IPolicyRow) {
    const bizIds = row.bk_biz_scope.map(item => item.bk_biz_id);
    if (window.localStorage) {
      window.localStorage.setItem('__bk-biz-id__', JSON.stringify(bizIds));
    }
    MainStore.setSelectedBiz(bizIds);
    this.$router.push({
      name: 'plugin',
      params: { policyId: row.id },
    });
  }
  public rowClassName({ row, rowIndex }: { row: IPolicyRow, rowIndex: number }) {
    let className = row.isGrayRule ? 'gray-rule-row' : '';
    if (!(!this.data[rowIndex + 1] || !this.data[rowIndex + 1].isGrayRule)) {
      className = `${className} not-bottom-row`;
    }
    return  row.enable ? className : `${className} row-disabled`;
  }
  public handleCellClass({ column, row }: { column: IBkColumn, row: IPolicyRow }) {
    return column.type === 'expand' && row.hasGrayRule ?  'hide-cell' : '';
  }
  private handleGotoTask(row: IPolicyRow) {
    if (row.job_result && row.job_result.job_id) {
      this.$router.push({
        name: 'taskDetail',
        params: { taskId: row.job_result.job_id },
      });
    }
  }
  private getRowOperateAuthInfo(row: IPolicyRow) {
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
  @debounceDecorate(300)
  private reCalcFlexibleTag() {
    const refs = this.$refs;
    Object.keys(refs).forEach((key) => {
      if (/flexibleTagRef/.test(key)) {
        (this.$refs[key] as any).reCalcOverflow();
      }
    });
  }
  private renderHeader(h: CreateElement) {
    return h(ColumnSetting, {
      props: {
        filterHead: true,
        localMark: this.localMark,
        value: this.filter,
      },
      on: {
        update: (data: Dictionary) => this.handleColumnUpdate(data),
      },
    });
  }
  private handleColumnUpdate(data: Dictionary) {
    this.filter = data;
    this.$forceUpdate();
  }
  private colspanHandle({ column }: { column: IBkColumn }) {
    if (column.property === 'colspanOperate') {
      return [1, 2];
    } if (column.property === 'colspanSetting') {
      return [0, 0];
    }
  }
}
</script>
<style lang="postcss" scoped>
.sub-title {
  margin-top: -16px;
}
.num {
  color: #3a84ff;
  cursor: pointer;
}
.success {
  color: #3fc06d;
}
.success {
  color: #3fc06d;
}
.warn {
  color: #ff9c01;
}
.error {
  color: #ea3636;
}
.text-gray {
  color: #c4c6cc;
}
.td-sys-icon {
  color: #979ba5;
}
>>> .row-disabled {
  color: #c4c6cc;
  .td-sys-icon {
    color: rgba(151, 155, 165, .4);
  }
}
.policy-tip-content {
  line-height: 20px;
  button {
    height: 20px;
    font-size: 12px;
  }
}
.gray-tag {
  margin-right: 4px;
  white-space: nowrap;
}
>>> .gray-rule-row {
  background: #fafbfd;
  &.not-bottom-row {
    td:first-child {
      border-bottom: 0;
    }
  }
}
>>> .abnormal-column .cell {
  padding-left: 0px;
  padding-right: 0px;
}
>>> .name-column .cell {
  padding-left: 6px;
}
.bk-table-row td {
  >>> &.is-first .cell {
    padding-left: 0;
    padding-right: 0;
  }
  .col-execution {
    padding: 5px 0;
    line-height: 20px;
    white-space: nowrap;
  }
}
>>> .hide-cell .cell {
  display: none;
}
>>> .bk-badge-wrapper .bk-badge.pinned.top-right {
  top: 6px;
}
>>> .bk-badge-wrapper .bk-badge.dot {
  width: 8px;
  height: 8px;
  min-width: 8px;
  border-color: #fff;
}
.plugin-rule-name {
  display: flex;
  align-items: center;
  .alias-text-btn {
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
  }
  .nc-icon-edit-2 {
    color: #979ba5;
    cursor: pointer;
    &:hover {
      color: #3a84ff;
    }
  }
}
.operate {
  display: flex;
  align-items: center;
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
    &:hover {
      color: #3a84ff;
      background: #dcdee5;
    }
  }
}
.loading-icon {
  display: inline-block;
  animation: loading 1s linear infinite;
  font-size: 14px;
  min-width: 24px;
  text-align: center;
}
.loading-name {
  margin-left: 7px;
}
</style>
