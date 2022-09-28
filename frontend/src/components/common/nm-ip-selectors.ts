import create from '@blueking/ip-selector/dist/vue2.6.x';
import '@blueking/ip-selector/dist//styles/vue2.6.x.css';
import * as IpChooserTopo from '@/api/modules/ipchooser_topo';
import * as IpChooserHost from '@/api/modules/ipchooser_host';
import { INodeType } from '@/types/plugin/plugin-type';

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

export type IStatic = 'alive_count' | 'no_alive_count' | 'total_count';

export interface IStatistics {
  [key: IStatic]: number
}

export interface IQuery {
  start?: number
  page_size?: number
  search_content?: string
  node_list: INode[]
}
export interface ISelectorValue {
  dynamic_group_list: Dictionary[]
  host_list: IHost[]
  node_list: INode[]
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
  created() {
    this.instance = create({
      panelList: this.panelList,
      unqiuePanelValue: true,
      nameStyle: 'kebabCase', // 'camelCase' | 'kebabCase'
      fetchTopologyHostCount: this.fetchTopologyHostCount, // 拉取topology
      fetchTopologyHostsNodes: this.fetchTopologyHostsNodes, // 静态拓扑 - 选中节点
      fetchNodesQueryPath: this.fetchNodesQueryPath, // 动态拓扑 - 勾选节点
      fetchHostAgentStatisticsNodes: this.fetchHostAgentStatisticsNodes, // 动态拓扑 - 勾选节点
      fetchTopologyHostIdsNodes: IpChooserTopo.queryHostIdInfos, // 根据多个拓扑节点与搜索条件批量分页查询所包含的主机 ID 信息(跨页全选)
      fetchHostsDetails: this.fetchHostsDetails, // 静态 - IP选择回显(host_id查不到时显示失效)
      fetchHostCheck: this.fetchHostCheck, // 手动输入 - 根据用户手动输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息
      // fetchDynamicGroups: IpChooserTopo.fetchDynamicGroup,
      // fetchHostsDynamicGroup: IpChooserTopo.fetchDynamicGroupHost,
      // fetchHostAgentStatisticsDynamicGroups: IpChooserTopo.fetchBatchGroupAgentStatistics,
      fetchCustomSettings: CustomSettingsService.fetchAll,
      updateCustomSettings: CustomSettingsService.update,
      fetchConfig: () => CustomSettingsService.fetchConfig,
    });
  },
  mounted() {
    console.log(this.$refs);
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
      if (node) {
        return Promise.resolve(list[0].child);
      }
      // this.topology = list;

      return Promise.resolve(list);
    },

    // 静态拓扑 - 选中节点(根据多个拓扑节点与搜索条件批量分页查询所包含的主机信息)
    fetchTopologyHostsNodes(query: IQuery) {
      if (!query.search_content) delete query.search_content;
      return IpChooserTopo.queryHosts({
        action: this.action,
        ...query,
      });
    },

    // 动态拓扑 - 勾选节点(查询多个节点拓扑路径)
    fetchNodesQueryPath(node: IFetchNode): Promise<Array<INode>[]> {
      // console.log('fetchNodesQueryPath', node);
      return IpChooserTopo.queryPath({ action: this.action, node_list: node.node_list }, {
        cancelPrevious: false,
      });
    },
    // 动态拓扑 - 勾选节点(获取多个拓扑节点的主机 Agent 状态统计信息)
    async fetchHostAgentStatisticsNodes(node: IFetchNode): Promise<{ agent_statistics: IStatistics, node: INode }[]> {
      // console.log('fetchHostAgentStatisticsNodes', node);
      const res = await IpChooserTopo.agentStatistics({ action: this.action, node_list: node.node_list });
      res.forEach((item) => {
        Object.assign(item.agent_statistics, {
          ...item.agent_statistics,
          not_alive_count: item.agent_statistics.no_alive_count,
        });
        delete item.agent_statistics.no_alive_count;
      });
      return Promise.resolve(res);
    },
    fetchHostsDetails(node) {
      console.log('fetchHostsDetails', node);
      return IpChooserHost.details({
        actio: this.action,
        all_scope: true,
        ...node,
      });
    },
    // 手动输入
    fetchHostCheck(node: IFetchNode) {
      console.log(node);
      return IpChooserHost.check({
        ...node,
        action: this.action,
        all_scope: true,
      });
    },
    change(value: { [key: string]: INode[] }) {
      this.$emit('change', value);
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
