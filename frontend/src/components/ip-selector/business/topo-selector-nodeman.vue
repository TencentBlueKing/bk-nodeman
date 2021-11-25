<template>
  <ip-selector
    ref="selector"
    class="ip-selector"
    v-bkloading="{ isLoading }"
    :key="selectorKey"
    :panels="panels"
    :height="height"
    :active.sync="active"
    :preview-data="previewData"
    :get-default-data="handleGetDefaultData"
    :get-search-table-data="handleGetSearchTableData"
    :dynamic-table-config="dynamicTableConfig"
    :static-table-config="staticTableConfig"
    :custom-input-table-config="staticTableConfig"
    :get-default-selections="getDefaultSelections"
    :preview-operate-list="previewOperateList"
    :preview-width="previewWidth"
    :default-checked-nodes="defaultCheckedNodes"
    :lazy-method="lazyMethod"
    :lazy-disabled="lazyDisabled"
    :default-expand-level="1"
    :search-data-options="searchDataOptions"
    :get-search-tree-data="getSearchTreeData"
    :tree-data-options="treeDataOptions"
    :default-active-name="defaultActiveName"
    :result-width="380"
    :default-selected-node="defaultSelectedNode"
    :get-search-result-selections="getSearchResultSelections"
    ip-key="inner_ip"
    @check-change="handleCheckChange"
    @remove-node="handleRemoveNode"
    @menu-click="handleMenuClick"
    @search-selection-change="handleSearchSelectionChange">
  </ip-selector>
</template>
<script lang="ts">
/* eslint-disable camelcase */
import { Vue, Component, Prop, Ref, Watch, Emit } from 'vue-property-decorator';
import IpSelector from '../index.vue';
import AgentStatus from '../components/agent-status.vue';
import {
  IPanel,
  ITableConfig,
  IPreviewData,
  IMenu,
  ITableCheckData,
  ITreeNode, IpType,
} from '../types/selector-type';
import { defaultSearch } from '../common/util';
import { retrieveBiz, fetchTopo, searchTopo } from '@/api/modules/cmdb';
import { listHost, nodeStatistic } from '@/api/modules/host_v2';
import { listHost as tableListHost } from '@/api/modules/host';
import { PluginStore } from '@/store';

@Component({
  name: 'topo-selector',
  components: {
    IpSelector,
  },
})
export default class TopoSelector extends Vue {
  @Prop({ default: 'TOPO', type: String }) private readonly nodeType!: IpType;
  @Prop({ default: () => [], type: Array }) private readonly checkedData!: any[];
  @Prop({ default: 280, type: Number }) private readonly previewWidth!: number;
  @Prop({ default: 0, type: [Number, String] }) private readonly height!: number |  string;
  @Prop({ default: () => [], type: Array }) private readonly action!: string[];
  @Prop({ default: false, type: Boolean }) private readonly customizeLimit!: boolean;

  @Ref('selector') private readonly selector!: IpSelector;

  // 当前激活tab
  private active = this.nodeType  === 'INSTANCE' ? 'static-topo' : 'dynamic-topo';
  // topo树数据
  private topoTree: ITreeNode[] = [];
  // 动态拓扑表格数据
  private topoTableData: any[] = [];
  // 动态TOPO树默认勾选数据
  private defaultCheckedNodes: (string | number)[] = [];
  // 静态表格数据
  private staticTableData: any[] = [];
  // 动态拓扑表格配置
  private dynamicTableConfig: ITableConfig[] = [];
  // 静态拓扑表格配置
  private staticTableConfig: ITableConfig[] = [];
  // 预览数据
  private previewData: IPreviewData[] = [];
  // 更多操作配置
  private previewOperateList: IMenu[] = [];
  // v-if方式渲染选择器时需要重置Key
  private selectorKey = 1;
  private searchDataOptions = {
    idKey: 'id',
    nameKey: 'name',
    pathKey: 'path',
  };
  // 唯一标识认准 biz_inst_id
  private treeDataOptions = {
    idKey: 'biz_inst_id',
  };
  // 默认激活预览面板
  private defaultActiveName = ['TOPO', 'INSTANCE'];
  private textMap: any = {
    RUNNING: window.i18n.t('正常'),
    TERMINATED: window.i18n.t('异常'),
    NOT_INSTALLED: window.i18n.t('未安装'),
  };
  private isLoading = false;
  // 默认勾选的节点
  private defaultSelectedNode = '0';

  private get isGrayRule(): boolean {
    return PluginStore.isGrayRule;
  }
  private get bizRange(): number[] {
    return PluginStore.hostsByBizRange;
  }
  private get panels(): IPanel[] {
    const panels: IPanel[] = [
      {
        name: 'dynamic-topo',
        label: this.$t('动态选择'),
        tips: this.$t('不能混用'),
        disabled: !!this.checkedData.length && ['static-topo', 'custom-input'].includes(this.active),
      },
      {
        name: 'static-topo',
        label: this.$t('静态选择'),
        tips: this.$t('不能混用'),
        disabled: !!this.checkedData.length && this.active === 'dynamic-topo',
      },
      {
        name: 'custom-input',
        label: this.$t('自定义输入'),
        tips: this.$t('不能混用'),
        disabled: !!this.checkedData.length && this.active === 'dynamic-topo',
      },
    ];
    return this.isGrayRule ? panels.filter(item => item.name !== 'dynamic-topo') : panels;
  }

  @Watch('active')
  private handleActiveChange() {
    this.staticTableData = [];
    this.topoTableData = [];
  }

  @Watch('checkedData', { immediate: true })
  private handleCheckedDataChange() {
    if (this.checkedData && this.checkedData.length) {
      const nodeTypeTextMap: any = {
        TOPO: this.$t('节点'),
        INSTANCE: 'IP',
      };
      const nodeTypeNameMap: any = {
        TOPO: 'path',
        INSTANCE: 'inner_ip',
      };
      this.previewData = [];
      this.previewData.push({
        id: this.nodeType,
        name: nodeTypeTextMap[this.nodeType],
        data: [...this.checkedData],
        dataNameKey: nodeTypeNameMap[this.nodeType],
      });
    }
  }

  private created() {
    this.previewOperateList = [
      {
        id: 'removeAll',
        label: this.$t('移除所有'),
      },
    ];
    this.dynamicTableConfig = [
      {
        prop: 'name', // === name
        label: this.$t('节点名称'),
      },
      {
        prop: 'host_count',
        label: this.$t('主机数量'),
      },
    ];
    this.staticTableConfig = [
      {
        prop: 'inner_ip',
        label: 'IP',
      },
      {
        prop: 'status',
        label: this.$t('Agent状态'),
        render: this.renderIpAgentStatus,
      },
      {
        prop: 'bk_cloud_name',
        label: this.$t('云区域'),
      },
      {
        prop: 'os_type',
        label: this.$t('操作系统'),
      },
    ];
  }

  private renderIpAgentStatus(row: any) {
    const statusMap: any = {
      RUNNING: 'running',
      TERMINATED: 'terminated',
      NOT_INSTALLED: 'unknown',
    };
    return this.$createElement(AgentStatus, {
      props: {
        type: 2,
        data: [
          {
            status: statusMap[row.status],
            count: row.agent_error_count,
            display: this.textMap[row.status],
          },
        ],
      },
    });
  }

  private renderAgentCountStatus(row: any) {
    const data: any[] = [];
    const statusList = ['RUNNING', 'TERMINATED', 'NOT_INSTALLED'];
    statusList.forEach((item: string) => {
      if (row[item]) {
        data.push({
          count: row[item],
          status: item,
          display: this.textMap[item],
        });
      }
    });
    return this.$createElement(AgentStatus, {
      props: {
        type: 0,
        data: data.length ? data : [{ count: 0 }],
      },
    });
  }

  private async lazyMethod(node: ITreeNode) {
    const { data } = node;
    if (data.children && data.children.length) {
      return {
        data: data.children,
        leaf: [],
      };
    }
    const nodes = await fetchTopo({ bk_biz_id: data.bk_biz_id, action: 'strategy_create' }).catch(() => ([]));
    // 缓存当前业务TOPO数据
    const bizNode = this.topoTree.find(item => item.biz_inst_id === data.biz_inst_id);
    bizNode && (bizNode.children = [...nodes]);
    return {
      data: nodes,
      leaf: [],
    };
  }

  private lazyDisabled(node: ITreeNode) {
    const { data } = node;
    if (data.type === 'biz') {
      return !data.has_permission;
    }
    return node.data.children.length === 0;
  }

  // 获取当前tab下默认数据
  private async handleGetDefaultData() {
    if (['dynamic-topo', 'static-topo'].includes(this.active)) {
      // 动态拓扑默认组件数据
      if (!this.topoTree.length) {
        let data = await retrieveBiz({ action: 'strategy_create' }).catch(() => ([]));
        if (this.bizRange.length) {
          data = data.filter((item: any) => this.bizRange.includes(item.bk_biz_id));
        }
        data.forEach((item: any) => {
          item.name =  item.bk_biz_name;
          item.biz_inst_id =  `${item.bk_biz_id}`;
          item.type = 'biz';
          item.children = [];
          item.action = this.action;
          item.disabled = !item.has_permission;
        });
        this.topoTree = data;
        this.active === 'dynamic-topo' && this.handleSetDefaultCheckedNodes();
      }
      return [
        {
          name: this.$t('全部业务'),
          children: this.topoTree,
          biz_inst_id: '0', // 根节点ID
        },
      ];
    }
  }

  // 异步加载设置叶子节点
  private setLeafNodes(data: ITreeNode[]) {
    return data.reduce<(string | number)[]>((pre, next) => {
      if (!next.children || next.children.length === 0) {
        pre.push(next.biz_inst_id);
      } else {
        pre.push(...this.setLeafNodes(next.children));
      }
      return pre;
    }, []);
  }

  private handleSetDefaultCheckedNodes() {
    // todo 待优化，多处调用，性能问题
    const { data = [] } = this.previewData.find(item => item.id === 'TOPO') || {};
    this.defaultCheckedNodes = this.getCheckedNodesIds(this.topoTree, data);
  }

  // 获取选中节点的ID集合
  private getCheckedNodesIds(nodes: any[], checkedData: any[] = []) {
    if (!checkedData.length) return [];
    return nodes.reduce<(string | number)[]>((pre, item) => {
      const { children = [], biz_inst_id = '', id } = item;
      const exist = checkedData.some(checkedData => checkedData.biz_inst_id === biz_inst_id);
      if (exist) {
        pre.push(id);
      }
      if (children.length) {
        pre.push(...this.getCheckedNodesIds(children, checkedData));
      }
      return pre;
    }, []);
  }

  // 获取表格数据（组件内部封装了交互逻辑）
  private async handleGetSearchTableData(params: any, type?: string): Promise<{
    total: number, data: any[] }> {
    if (this.active === 'dynamic-topo') {
      return await this.getDynamicTopoTableData(params, type);
    }
    if (this.active === 'static-topo') {
      return await this.getStaticTableData(params, type);
    }
    if (this.active === 'custom-input') {
      if (this.customizeLimit && PluginStore.hostsByScopeRange) {
        params.scope = PluginStore.hostsByScopeRange;
      }
      return await this.getCustomInput(params);
    }
    return {
      total: 0,
      data: [],
    };
  }

  // 获取动态topo表格数据
  private async getDynamicTopoTableData(params: any, type?: string) {
    let data = [];
    const { selections = [], parentNode = null, current = 1, limit = -1, tableKeyword = '' } = params;
    let tmpSelections = selections;
    if (['page-change', 'selection-change', 'keyword-change'].includes(type)) {
      // 业务节点需要初始化默认子节点信息
      if (!selections.length && parentNode && parentNode.data.type === 'biz') {
        const { data = [] } = await this.lazyMethod(parentNode);
        tmpSelections = data;
      } else if (!selections.length && parentNode) {
        // 叶子节点就展示当前节点信息
        tmpSelections = [parentNode.data];
        if (parentNode.index === 0 && !selections.length) return { total: 0, data: [] }; // 根节点下无业务的时候不加载后续接口
      }
      if (!!tmpSelections.length) {
        if (tableKeyword) {
          // 前端过滤一遍之后传给后端，带回 bk_inst_id
          tmpSelections = defaultSearch(this.topoTableData, tableKeyword);
        }
        data = await nodeStatistic(this.getParams(
          tmpSelections.slice(limit * (current - 1), limit * current),
          parentNode,
        )).catch(() => ([]));
        this.topoTableData = tmpSelections.map(item => ({
          ...item,
          bk_inst_name: item.name,
        }));
      }
    // } else {
    //   const { tableKeyword = '' } = params
    //   tmpSelections = defaultSearch(this.topoTableData, tableKeyword)
    //   data = tmpSelections.slice(limit * (current - 1), limit * current)
    }

    return {
      total: tmpSelections.length,
      data,
    };
  }

  // 获取静态表格数据
  private async getStaticTableData(params: any, type?: string) {
    let data = [];
    let count = 0;
    const { selections = [], parentNode = null, current = 1, limit = 20, tableKeyword = '' } = params;
    if (['page-change', 'selection-change'].includes(type as string)) {
      if (!!selections.length) {
        const params = this.getParams(selections, parentNode, current, limit);
        if (PluginStore.hostsByScopeRange) {
          params.scope = PluginStore.hostsByScopeRange;
        }
        const { list = [], total } = await listHost(params)
          .catch(() => ({ list: [] }));
        this.staticTableData = list;
        data = list;
        count = total;
      }
    }
    if (['keyword-change'].includes(type as string)) {
      const params: Dictionary = {
        page: current,
        pagesize: limit,
        extra_data: ['job_result', 'identity_info'],
      };
      const { conditions, bkBizId } = this.getStaticTableSearchParams(selections, parentNode, tableKeyword);
      params.conditions = conditions;
      if (bkBizId.length) {
        params.bk_biz_id = bkBizId;
      }
      const { list = [], total } = await tableListHost(params).catch(() => ({ list: [] }));
      this.staticTableData = list;
      data = list;
      count = total;
    }
    // else {
    //   const { tableKeyword = '' } = params
    //   data = defaultSearch(this.staticTableData, tableKeyword)
    // }

    return {
      total: count,
      data,
    };
  }

  // 获取自定义输入表格数据
  private async getCustomInput(params: any) {
    const { ipList = [], scope } = params;
    const { list = [], total } = await listHost({
      pagesize: -1,
      action: 'strategy_create',
      conditions: [
        {
          key: 'inner_ip',
          value: ipList,
        },
      ],
      scope,
    }).catch(() => ({ list: [] }));
    return {
      total,
      data: list,
    };
  }

  private getParams(nodes: any[], parentNode: any, current?: number, limit?: number) {
    const params: { [key: string]: any } = {
      page: current || 1,
      pagesize: limit || -1,
      action: 'strategy_create',
    };
    // 部署节点属性组合必须是 dynamic(bk_biz_id, bk_obj_id, bk_inst_id) 或者 static(bk_biz_id, bk_host_id)
    if (this.active === 'dynamic-topo') {
      params.agent_status_count = true;
      params.nodes = nodes.map(item => ({
        ...item,
        bk_inst_name: item.name,
        bk_inst_id: item.id,
        bk_obj_id: item.type,
        bk_biz_id: item.bk_biz_id || item.id,
      }));
    } else {
      if (!parentNode) {
        params.bk_biz_id = nodes[0].children.map((biz: any) => biz.bk_biz_id || biz.id);
      } else {
        if (nodes.length === 1 && nodes[0].type === 'biz') {
          params.bk_biz_id = [nodes[0].bk_biz_id || nodes[0].id];
        } else {
          params.nodes = nodes.map(item => ({
            ...item,
            bk_inst_id: item.id,
            bk_obj_id: item.type,
            bk_biz_id: item.bk_biz_id,
          }));
        }
      }
    }
    return params;
  }
  // 同agent管理 - agent搜索参数条件
  private getStaticTableSearchParams(nodes: any[], parentNode: any, tableKeyword: string) {
    const params: { [key: string]: any } = {
      bkBizId: [],
      conditions: [
        { key: 'query', value: tableKeyword },
      ],
    };
    if (parentNode) {
      const [{ bk_biz_id: bkBizId, type, id }] = nodes;
      params.bkBizId.push(bkBizId);

      if (['set', 'module'].includes(type)) {
        const topoCondition: Dictionary = {
          key: 'topology',
          value: {
            bk_biz_id: bkBizId,
          },
        };
        if (type === 'set') {
          topoCondition.value.bk_set_ids = [id];
        } else {
          topoCondition.value.bk_set_ids = [parentNode.data.id];
          topoCondition.value.bk_module_ids = [id];
        }
        params.conditions.push(topoCondition);
      }
    }
    return params;
  }

  // 表格check表更事件(请勿修改selectionsData里面的数据)
  @Emit('check-change')
  private handleCheckChange(selectionsData: ITableCheckData) {
    if (this.active === 'dynamic-topo') {
      this.dynamicTableCheckChange(selectionsData);
      this.handleSetDefaultCheckedNodes();
    }
    if (['static-topo', 'custom-input'].includes(this.active)) {
      this.staticIpTableCheckChange(selectionsData);
    }
    return this.getCheckedData();
  }

  // 动态类型表格check事件
  private dynamicTableCheckChange(selectionsData: ITableCheckData) {
    const { selections = [], excludeData = [] } = selectionsData;
    const index = this.previewData.findIndex(item => item.id === 'TOPO');
    if (index > -1) {
      const { data } = this.previewData[index];
      selections.forEach((select) => {
        const index = data.findIndex(data => data.biz_inst_id === select.biz_inst_id);

        index === -1 && data.push(select);
      });
      excludeData.forEach((exclude) => {
        const index = data.findIndex(data => data.biz_inst_id === exclude.biz_inst_id);

        index > -1 && data.splice(index, 1);
      });
    } else {
      // 初始化分组信息
      this.previewData.push({
        id: 'TOPO',
        name: this.$t('节点'),
        data: [...selections],
        dataNameKey: 'path',
      });
    }
  }

  // 静态类型的表格check事件
  private staticIpTableCheckChange(selectionsData: ITableCheckData) {
    const { selections = [], excludeData = [] } = selectionsData;
    const index = this.previewData.findIndex(item => item.id === 'INSTANCE');
    if (index > -1) {
      const { data } = this.previewData[index];
      selections.forEach((select) => {
        const index = data.findIndex(data => this.identityIp(data, select));

        index === -1 && data.push(select);
      });
      excludeData.forEach((exclude) => {
        const index = data.findIndex(data => this.identityIp(data, exclude));

        index > -1 && data.splice(index, 1);
      });
    } else {
      // 初始化分组信息
      this.previewData.push({
        id: 'INSTANCE',
        name: this.$t('IP'),
        data: [...selections],
        dataNameKey: 'inner_ip',
      });
    }
  }

  // 判断IP是否一样
  private identityIp(pre: any, next: any) {
    // bk_host_id 唯一
    return pre.bk_host_id === next.bk_host_id;
  }

  // 移除节点
  @Emit('check-change')
  private handleRemoveNode({ child, item }: { child: any, item: IPreviewData }) {
    const group = this.previewData.find(data => data.id === item.id);
    if (group) {
      const index = group.data.findIndex((data) => {
        if (group.id === 'TOPO') {
          return data.biz_inst_id === child.biz_inst_id;
        }
        return this.identityIp(data, child);
      });
      index > -1 && group.data.splice(index, 1);
    }
    this.selector.handleGetDefaultSelections();
    item.id === 'TOPO' && this.handleSetDefaultCheckedNodes();
    return this.getCheckedData();
  }

  // 当前check项
  private getDefaultSelections(row: any) {
    if (this.active === 'dynamic-topo') {
      const group = this.previewData.find(data => data.id === 'TOPO');
      return group?.data.some(data => data.biz_inst_id === row.biz_inst_id);
    }
    if (['static-topo', 'custom-input'].includes(this.active)) {
      const group = this.previewData.find(data => data.id === 'INSTANCE');
      return group?.data.some(data => this.identityIp(data, row));
    }
    return false;
  }

  // tree搜索勾选事件
  private async handleSearchSelectionChange(checkData: ITableCheckData) {
    const { selections = [], excludeData = [] } = checkData;
    let data = selections;
    let exclude = excludeData;
    if (this.active === 'static-topo' && !!selections.length) {
      this.isLoading = true;
      const { list = [] } = await listHost(this.getParams(selections, {})).catch(() => ({ list: [] }));
      this.isLoading = false;
      data = list;
      exclude = [];
    }
    const selectionsData: ITableCheckData = {
      selections: data,
      excludeData: exclude,
    };
    this.handleCheckChange(selectionsData);
  }

  // 获取当前拓扑树搜索面板的默认勾选项
  private getSearchResultSelections(data: any) {
    const group = this.previewData.find(data => data.id === 'TOPO');
    return group?.data.some(item => data.biz_inst_id === item.biz_inst_id);
  }

  // 预览菜单点击事件
  private handleMenuClick({ menu, item }: { menu: IMenu, item: IPreviewData }) {
    if (menu.id === 'removeAll') {
    //   const group = this.previewData.find(data => data.id === item.id)
    //   group && (group.data = [])
      const index = this.previewData.findIndex(data => data.id === item.id);
      index > -1 && this.previewData.splice(index, 1);
      this.selector.handleGetDefaultSelections();
      item.id === 'TOPO' && this.handleSetDefaultCheckedNodes();
      this.$emit('check-change', this.getCheckedData());
    }
  }

  // 获取勾选的数据
  private getCheckedData() {
    // 默认只能选择一种方式
    const previewData = this.previewData.filter(item => item.data && item.data.length);
    const [group] = previewData;
    if (previewData.length !== 1 || group.data.length === 0) {
      return {
        type: this.active === 'dynamic-topo' ? 'TOPO' : 'INSTANCE',
        data: [],
      };
    }
    return {
      type: group.id,
      data: group.data,
    };
  }

  private resize() {
    this.$nextTick(() => {
      this.selectorKey = Math.random() * 10;
    });
  }

  private async getSearchTreeData({ treeKeyword }: { treeKeyword: string }) {
    const { nodes } = await searchTopo({
      kw: treeKeyword,
      action: 'strategy_create',
    }).catch(() => ({ total: 0, nodes: [] }));
    // 搜索结果ID字段和topo保持一致，便于对比
    return nodes.map((node: any) => ({
      ...node,
      biz_inst_id: `${node.id}`,
    }));
  }
}
</script>
<style lang="scss" scoped>
.ip-selector {
  width: 100%;
  flex: 1;
  min-height: 300px;
  /deep/ .topo-tree {
    /* stylelint-disable-next-line declaration-no-important */
    height: 100% !important;
  }
}
</style>
