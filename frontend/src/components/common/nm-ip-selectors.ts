import create from '@blueking/ip-selector/dist/index';
import '@blueking/ip-selector/dist/styles/index.css';
import * as IpChooserTopo from '@/api/modules/ipchooser_topo';
import * as IpChooserHost from '@/api/modules/ipchooser_host';
import { INodeType } from '@/types/plugin/plugin-type';
import { PluginStore } from '@/store';

export interface IMeta {
  bk_biz_id: number
  scope_id: string
  scope_type: 'biz'
}

export interface INode {
  instance_id: number
  object_id: 'module' | 'set' | 'biz'
  meta: IMeta
}
export interface IHost {
  host_id: number
  meta: IMeta
}
export interface ITarget {
  // node_type = 'INSTANCE' => bk_host_id  ||  'TOPO' => bk_obj_id && bk_inst_id
  bk_biz_id: number,
  bk_obj_id?: 'set' | 'module'
  bk_inst_id?: number
  bk_host_id?: number
  biz_inst_id?: string
  path?: string
  children?: ITarget[]
}

export interface ITreeItem extends INode {
  count: number
  expanded: boolean
  object_name: string
  instance_name: string
  child: ITreeItem[]
}
export interface IFetchNode {
  node_list: INode[]
}

export type IStatic = 'alive_count' | 'not_alive_count' | 'total_count';

export interface IStatistics {
  [key: IStatic]: number
}

export interface IQuery {
  start?: number
  page_size?: number
  search_content?: string
  node_list: INode[]
  // 以上 IP-selector标准参数
  all_scope?: boolean
  search_limit?: {
    node_list?: INode[]
    host_ids?: number[]
  } // 灰度策略的限制范围
}
export interface ISelectorValue {
  dynamic_group_list: Dictionary[]
  host_list: IHost[]
  node_list: INode[]
}
export interface IScope {
  // object_type?: IObjectType
  node_type: INodeType
  nodes: ITarget[]
}

/**
 * 转换成标准的IP选择器的选中数据
 */
export function toSelectorNode(nodes: ITarget[], nodeType: INodeType) {
  if (!nodeType || nodes.some(node => node.meta)) return nodes;
  if (nodeType === 'INSTANCE') {
    return nodes.map(item => ({
      host_id: item.bk_host_id,
      meta: {
        scope_type: 'biz',
        scope_id: `${item.bk_biz_id}`,
        bk_biz_id: item.bk_biz_id,
      },
    }));
  }
  return nodes.map(item => ({
    object_id: item.bk_obj_id,
    instance_id: item.bk_inst_id,
    meta: {
      scope_type: 'biz',
      scope_id: `${item.bk_biz_id}`,
      bk_biz_id: item.bk_biz_id,
    },
  }));
}

/**
 * 转换为策略需要的选中数据
 */
export function toStrategyNode(nodes: Array<INode | IHost>, nodeType: INodeType) {
  if (!nodeType || nodes.some(node => !node.meta)) return nodes;
  if (nodeType === 'INSTANCE') {
    return nodes.map((item: IHost) => ({
      bk_biz_id: item.meta.bk_biz_id,
      bk_host_id: item.host_id,
    }));
  }
  return nodes.map((item: INode) => ({
    bk_obj_id: item.object_id,
    bk_inst_id: item.instance_id,
    bk_biz_id: item.meta.bk_biz_id,
  }));
}


const CustomSettingsService = {
  fetchAll: () => Promise.resolve([]),
  update: () => Promise.resolve([]),
  fetchConfig: () => Promise.resolve([]),
};

export default {
  name: 'NmIpSelector',
  props: {
    panelList: {
      type: Array,
      default: () => [],
    },
    value: {
      type: Object as ISelectorValue,
      default: () => ({}),
    },
    action: {
      type: String,
      default: 'strategy_create',
      // type: Array,
      // default: () => [],
    },
  },
  data() {
    return {
      instance: null,
      topology: [],
    };
  },
  computed: {
    isGrayRule() {
      return PluginStore.isGrayRule;
    },
  },
  created() {
    this.instance = create({
      panelList: this.panelList,
      unqiuePanelValue: true,
      nameStyle: 'kebabCase', // 'camelCase' | 'kebabCase'
      fetchTopologyHostCount: this.fetchTopologyHostCount, // 拉取topology
      fetchTopologyHostsNodes: (query: IQuery) => this.fetchTopologyHostsNodes(query, 'queryHosts'), // 静态拓扑 - 选中节点
      fetchNodesQueryPath: this.fetchNodesQueryPath, // 动态拓扑 - 勾选节点
      fetchHostAgentStatisticsNodes: this.fetchHostAgentStatisticsNodes, // 动态拓扑 - 勾选节点
      fetchTopologyHostIdsNodes: (query: IQuery) => this.fetchTopologyHostsNodes(query, 'queryHostIdInfos'), // 根据多个拓扑节点与搜索条件批量分页查询所包含的主机
      fetchHostsDetails: this.fetchHostsDetails, // 静态 - IP选择回显(host_id查不到时显示失效)
      fetchHostCheck: this.fetchHostCheck, // 手动输入 - 根据用户手动输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息
      // fetchDynamicGroups: IpChooserTopo.fetchDynamicGroup,
      // fetchHostsDynamicGroup: IpChooserTopo.fetchDynamicGroupHost,
      // fetchHostAgentStatisticsDynamicGroups: IpChooserTopo.fetchBatchGroupAgentStatistics,
      fetchCustomSettings: CustomSettingsService.fetchAll,
      updateCustomSettings: CustomSettingsService.update,
      fetchConfig: () => CustomSettingsService.fetchConfig,
      hostViewFieldRender: host => host.host_id,
    });
  },
  methods: {
    // 拉取topology
    async fetchTopologyHostCount(node?: INode): Promise<ITreeItem[]> {
      const params = {
        action: 'strategy_create',
      };
      if (node) {
        params.scope_list =  [node?.meta || {}];
      } else {
        params.all_scope =  true;
      }
      const list = await IpChooserTopo.trees(params);
      let data = node ? list[0].child : list;
      if (this.isGrayRule && !node) {
        // 灰度 - 只过滤到业务; // 过滤topo子节点需要考虑只选中子级的情况,且静态topo未统计节点信息
        data = data.filter(item => PluginStore.hostsByBizRange.includes(item.instance_id));
      }
      return Promise.resolve(data);
    },

    // 选中节点(根据多个拓扑节点与搜索条件批量分页查询所包含的主机信息)
    fetchTopologyHostsNodes(query: IQuery, method: string) {
      if (!query.search_content) delete query.search_content;
      const params = this.reviseParamsByGray({ action: this.action, ...query });
      return IpChooserTopo[method](params);
    },

    // 动态拓扑 - 勾选节点(查询多个节点拓扑路径)
    fetchNodesQueryPath(node: IFetchNode): Promise<Array<INode>[]> {
      return IpChooserTopo.queryPath({ action: this.action, node_list: node.node_list }, {
        cancelPrevious: false,
      });
    },
    // 动态拓扑 - 勾选节点(获取多个拓扑节点的主机 Agent 状态统计信息)
    async fetchHostAgentStatisticsNodes(node: IFetchNode): Promise<{ agent_statistics: IStatistics, node: INode }[]> {
      return IpChooserTopo.agentStatistics({ action: this.action, node_list: node.node_list });
    },
    fetchHostsDetails(node) {
      return IpChooserHost.details({
        actio: this.action,
        all_scope: true,
        ...node,
      });
    },
    // 手动输入
    fetchHostCheck(node: IFetchNode) {
      const params = this.reviseParamsByGray({ ...node, action: this.action, all_scope: true, saveScope: true });
      return IpChooserHost.check(params);
    },
    change(value: { [key: string]: INode[] }) {
      this.$emit('change', value);
    },

    // 灰度策略 - 修正相关查询接口的参数
    reviseParamsByGray(params: IQuery): IQuery {
      if (this.isGrayRule) {
        if (!params.saveScope && params.all_scope) delete params.all_scope;
        if (params.saveScope) delete params.saveScope;
        const { nodes = [], node_type } = PluginStore.hostsByScopeRange as IScope;
        const isTopo = node_type === 'TOPO';
        params.search_limit = {
          [isTopo ? 'node_list' : 'host_ids']: isTopo
            ? toSelectorNode(nodes, node_type)
            : nodes.map(item => item.bk_host_id),
        };
      }
      return params;
    },
  },
  render(h) {
    return h(this.instance, {
      ref: 'ipSelector',
      props: {
        mode: 'section',
        value: this.value,
        // service: {
        //   fetchNodesQueryPath() {} // 灰度
        // }
      },
      on: {
        change: this.change,
      },
    });
  },
};
