<template>
  <ServiceTemplate
    ref="service"
    :get-default-data="getDefaultData"
    :get-search-table-data="getSearchTableData"
    :get-default-selections="getDefaultSelections"
    :template-table-config="clusterTableConfig"
    :template-options="clusterOptions"
    :service-template-placeholder="clusterTemplatePlaceholder"
    :left-panel-width="leftPanelWidth"
    @check-change="handleCheckChange">
  </ServiceTemplate>
</template>
<script lang="ts">
import { Component, Vue, Prop, Emit, Ref } from 'vue-property-decorator';
import ServiceTemplate from './service-template.vue';
import { SearchDataFuncType, ITemplateDataOptions, ITableConfig, ITableCheckData } from '../types/selector-type';

// 集群
@Component({
  name: 'cluster',
  components: {
    ServiceTemplate,
  },
})
export default class Cluster extends Vue {
// 获取组件初始化数据
  @Prop({ type: Function, required: true }) private readonly getDefaultData!: Function;
  // 表格搜索数据
  @Prop({ type: Function, required: true }) private readonly getSearchTableData!: SearchDataFuncType;
  @Prop({ type: Function }) private readonly getDefaultSelections!: Function;
  @Prop({ default: () => ({
    idKey: 'bk_inst_id',
    childrenKey: 'instances_count',
    labelKey: 'bk_inst_name',
  }), type: Object }) private readonly clusterOptions!: ITemplateDataOptions;
  // 表格字段配置
  @Prop({ default: () => [], type: Array }) private readonly clusterTableConfig!: ITableConfig[];
  @Prop({ default: '', type: String }) private readonly clusterTemplatePlaceholder!: string;
  @Prop({ default: 240, type: [Number, String] }) private readonly leftPanelWidth!: number | string;

  @Ref('service') private readonly serviceRef!: ServiceTemplate;

  @Emit('check-change')
  private handleCheckChange(data: ITableCheckData) {
    return data;
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering
  public handleGetDefaultSelections() {
    this.serviceRef && this.serviceRef.handleGetDefaultSelections();
  }
}
</script>
<style lang="scss" scoped>

</style>
