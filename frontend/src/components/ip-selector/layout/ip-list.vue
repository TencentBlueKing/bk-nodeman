<template>
  <div class="ip-list" ref="ipListWrapper" v-bkloading="{ isLoading: isLoading && !disabledLoading }">
    <bk-input
      clearable
      right-icon="bk-icon icon-search"
      v-model="tableKeyword"
      :placeholder="ipListPlaceholder"
      @change="handleKeywordChange">
    </bk-input>
    <slot name="tab"></slot>
    <IpSelectorTable
      ref="table"
      class="ip-list-table mt10"
      :data="tableData"
      :config="ipListTableConfig"
      :pagination="pagination"
      :max-height="maxHeight"
      :default-selections="defaultSelections"
      :show-selection-column="showSelectionColumn"
      :empty-text="emptyText"
      @page-change="handlePageChange"
      @check-change="handleCheckChange"
      @page-limit-change="handleLimitChange">
    </IpSelectorTable>
  </div>
</template>
<script lang="ts">
import { Component, Vue, Prop, Emit, Ref, Watch } from 'vue-property-decorator';
import { Debounce } from '../common/util';
import IpSelectorTable from '../components/ip-selector-table.vue';
import {
  ITableConfig,
  SearchDataFuncType,
  IipListParams,
  IPagination,
  ITableCheckData } from '../types/selector-type';

// IP列表
@Component({
  name: 'ip-list',
  components: {
    IpSelectorTable,
  },
})
export default class IpList extends Vue {
  // 提交变更时调用该方法获取数据
  @Prop({ type: Function, required: true }) private readonly getSearchTableData!: SearchDataFuncType;
  @Prop({ type: Function }) private readonly getDefaultSelections!: Function;

  @Prop({ default: '', type: String }) private readonly ipListPlaceholder!: string;
  // 表格字段配置
  @Prop({ default: () => [], type: Array }) private readonly ipListTableConfig!: ITableConfig[];
  // 每页数
  @Prop({ default: 20, type: Number }) private readonly limit!: number;
  @Prop({ default: 0, type: Number }) private readonly slotHeight!: number;
  @Prop({ default: true, type: Boolean }) private readonly showSelectionColumn!: boolean;
  // 禁用组件的loading状态
  @Prop({ default: false, type: Boolean }) private readonly disabledLoading!: boolean;
  @Prop({ default: '', type: String }) private readonly emptyText!: string;

  @Ref('ipListWrapper') private readonly ipListWrapperRef!: HTMLElement;
  @Ref('table') private readonly tableRef!: IpSelectorTable;

  private isLoading = false;
  // 前端分页时全量数据
  private fullData: any[] = [];
  private frontendPagination = false;
  private tableData: any[] = [];
  private tableKeyword = '';
  private pagination: IPagination = {
    current: 1,
    limit: this.limit,
    count: 0,
    small: true,
    showLimit: false,
    showTotalCount: false,
    align: 'center',
    limitList: [20, 50, 100],
  };
  private maxHeight = 400;
  private defaultSelections: any[] = [];

  @Watch('slotHeight')
  private handleSlotHeightChange() {
    this.computedTableLimit();
  }

  private created() {
    this.handleGetDefaultData();
  }

  private mounted() {
    this.computedTableLimit();
  }

  private computedTableLimit() {
    // 表格最大高度， 数字76: 去除 输入框 + margin + 分页组件 + margin 的高度
    this.maxHeight = this.ipListWrapperRef.clientHeight - this.slotHeight - 86;
    // 表格分页条数，数字42: 去除表格header的高度
    const limit = Math.floor((this.maxHeight - 42) / 42);
    if (!this.pagination.limitList?.includes(limit)) {
      this.pagination.limitList?.push(limit);
    }
    this.pagination.limit = limit;
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering
  public handleGetDefaultData(type = '') {
    this.pagination.current = 1;
    this.pagination.count = 0;
    this.tableRef && this.tableRef.resetCheckedStatus();
    this.handleGetSearchData(type);
  }
  // eslint-disable-next-line @typescript-eslint/member-ordering
  public handleGetDefaultSelections() {
    // 获取默认勾选项
    this.defaultSelections = this.tableData.filter(row => this.getDefaultSelections
        && !!this.getDefaultSelections(row));
  }
  // eslint-disable-next-line @typescript-eslint/member-ordering
  public selectionAllData() {
    this.$nextTick(() => {
      !!this.tableData.length && this.tableRef && this.tableRef.handleSelectionChange({ value: 2, type: 'all' });
    });
  }
  public clearTableKeyWord() {
    this.tableKeyword = '';
  }

  private async handleGetSearchData(type = '') {
    try {
      this.isLoading = true;
      const params: IipListParams = {
        current: this.pagination.current,
        limit: this.pagination.limit,
        tableKeyword: this.tableKeyword,
      };
      const { total, data } = await this.getSearchTableData(params, type);
      if (data.length > this.pagination.limit) {
        this.frontendPagination = true;
        this.fullData = data;
        // 如果未分页，则前端自动分页
        const { limit, current } = this.pagination;
        this.tableData = data.slice(limit * (current - 1), limit * current);
      } else {
        this.frontendPagination = false;
        this.tableData = data || [];
      }
      this.pagination.count = total || 0;
      this.handleGetDefaultSelections();
    } catch (err) {
      console.log(err);
    } finally {
      this.isLoading = false;
    }
  }

  private handlePageChange(page: number) {
    if (page === this.pagination.current) return;

    this.pagination.current = page;
    this.handleGetSearchData('page-change');
  }

  private handleLimitChange(limit: number) {
    this.pagination.limit = limit;
    this.handleGetSearchData('limit-change');
  }

  @Debounce(300)
  private handleKeywordChange() {
    this.handleGetDefaultData('keyword-change');
  }

  @Emit('check-change')
  private handleCheckChange(data: ITableCheckData) {
    const { selections, excludeData, checkType, checkValue } = data;
    let tmpSelections = selections;
    let tmpExcludeData = excludeData;
    // 前端分页
    if (this.frontendPagination && checkType === 'all') {
      // 跨页全选
      if (checkValue === 2) {
        tmpSelections = this.fullData.filter(item => excludeData?.indexOf(item) === -1);
      } else if (checkValue === 0) {
        tmpExcludeData = this.fullData.filter(item => selections.indexOf(item) === -1);
      }
    }

    return {
      selections: tmpSelections,
      excludeData: tmpExcludeData,
      checkType,
    };
  }
}
</script>
<style lang="scss" scoped>
.ip-list {
  height: 100%;
  .table-tab {
    display: flex;
    background-image: linear-gradient(transparent 36px,#dcdee5 0);
    &-item {
      padding: 10px 0 8px 0;
      margin-right: 20px;
      cursor: pointer;
      &.active {
        color: #3a84ff;
        border-bottom: 2px solid #3a84ff;
      }
    }
  }
}
</style>
