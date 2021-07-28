<template>
  <DynamicTopo
    ref="dynamicTopo"
    :get-default-data="getDefaultData"
    :get-search-table-data="getSearchTableData"
    :get-search-tree-data="getSearchTreeData"
    :result-width="resultWidth"
    :search-data-options="searchDataOptions"
    :tree-data-options="treeDataOptions"
    :limit="limit"
    :transform-to-children="false"
    :show-count="false"
    :dynamic-table-config="staticTableConfig"
    :get-default-selections="getDefaultSelections"
    :lazy-method="lazyMethod"
    :lazy-disabled="lazyDisabled"
    :default-expand-level="defaultExpandLevel"
    :expand-on-click="expandOnClick"
    :left-panel-width="leftPanelWidth"
    :default-selected-node="defaultSelectedNode"
    @check-change="handleTableCheckChange"
    @search-selection-change="handleSearchSelectionChange">
  </DynamicTopo>
</template>
<script lang="ts">
import DynamicTopo from './dynamic-topo.vue';
import { Component, Prop, Vue, Emit, Ref } from 'vue-property-decorator';
import {
  ITableConfig,
  SearchDataFuncType,
  ISearchDataOption,
  ITableCheckData,
} from '../types/selector-type';

@Component({ name: 'static-topo', components: { DynamicTopo } })
export default class StaticTopo extends Vue {
  // 获取组件初始化数据
  @Prop({ type: Function, required: true }) private readonly getDefaultData!: Function;
  // 表格搜索数据
  @Prop({ type: Function, required: true }) private readonly getSearchTableData!: SearchDataFuncType;
  // 树搜索数据
  @Prop({ type: Function }) private readonly getSearchTreeData!: Function;
  @Prop({ type: Function }) private readonly getDefaultSelections!: Function;

  // tree搜索结果面板默认宽度
  @Prop({ default: 'auto', type: [Number, String] }) private readonly resultWidth!: number | string;
  // 搜索数据配置
  @Prop({ default: () => ({}), type: Object }) private readonly searchDataOptions!: ISearchDataOption;
  // 节点数据配置
  @Prop({ default: () => ({}), type: Object }) private readonly treeDataOptions!: any;
  // 每页数
  @Prop({ default: 20, type: Number }) private readonly limit!: number;
  // 表格字段配置
  @Prop({ default: () => [], type: Array }) private readonly staticTableConfig!: ITableConfig[];
  // 树懒加载方法
  @Prop({ type: Function }) private readonly lazyMethod!: Function;
  @Prop({ type: [Function, Boolean] }) private readonly lazyDisabled!: Function;
  @Prop({ default: 2, type: Number }) private readonly defaultExpandLevel!: number;
  @Prop({ default: false, type: Boolean }) private readonly expandOnClick!: boolean;
  @Prop({ default: 240, type: [Number, String] }) private readonly leftPanelWidth!: number | string;
  // 默认选中的节点
  @Prop({ default: '', type: [String, Number] }) private readonly defaultSelectedNode!: string | number;

  @Ref('dynamicTopo') private readonly dynamicTopoRef!: DynamicTopo;

  @Emit('check-change')
  private handleTableCheckChange(data: ITableCheckData) {
    return data;
  }
  @Emit('search-selection-change')
  private handleSearchSelectionChange(selections: any[]) {
    return selections;
  }
  // eslint-disable-next-line @typescript-eslint/member-ordering
  public handleGetDefaultSelections() {
    this.dynamicTopoRef && this.dynamicTopoRef.handleGetDefaultSelections();
  }
}
</script>
