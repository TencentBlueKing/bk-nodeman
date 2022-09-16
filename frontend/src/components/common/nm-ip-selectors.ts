import create from '@blueking/ip-selector/dist/vue2.6.x';
import '@blueking/ip-selector/dist//styles/vue2.6.x.css';
import * as IpChooserTopo from '@/api/modules/ipchooser_topo';
import * as IpChooserHost from '@/api/modules/ipchooser_host';

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

const CustomSettingsService = {
  fetchAll: () => Promise.resolve([]),
  update: () => Promise.resolve([]),
};

export default {
  name: 'NmIpSelector',
  props: {
    action: {
      type: String,
      default: 'strategy_create',
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
      panelList: ['staticTopo', 'dynamicTopo', 'manualInput'],
      unqiuePanelValue: true,
      nameStyle: 'kebabCase', // 'camelCase' | 'kebabCase'
      fetchTopologyHostCount: this.fetchTopologyHostCount, // 拉取topology
      fetchTopologyHostsNodes: this.fetchTopologyHostsNodes, // 静态拓扑 - 选中节点
      fetchNodesQueryPath: this.fetchNodesQueryPath, // 动态拓扑 - 勾选节点
      fetchHostAgentStatisticsNodes: this.fetchHostAgentStatisticsNodes, // 动态拓扑 - 勾选节点
      fetchTopologyHostIdsNodes: IpChooserTopo.queryHostIdInfos, // 根据多个拓扑节点与搜索条件批量分页查询所包含的主机 ID 信息(跨页全选)
      fetchHostsDetails: this.fetchHostsDetails,
      fetchHostCheck: this.fetchHostCheck, // 手动输入 - 根据用户手动输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息
      // fetchDynamicGroups: IpChooserTopo.fetchDynamicGroup,
      // fetchHostsDynamicGroup: IpChooserTopo.fetchDynamicGroupHost,
      // fetchHostAgentStatisticsDynamicGroups: IpChooserTopo.fetchBatchGroupAgentStatistics,
      fetchCustomSettings: CustomSettingsService.fetchAll,
      updateCustomSettings: CustomSettingsService.update,
      fetchConfig: () => Promise.resolve({}),
    });
  },
  mounted() {
    console.log(this.$refs);
  },
  methods: {
    // 拉取topology
    async fetchTopologyHostCount(node?: INode): Promise<ITreeItem[]> {
      console.log(node, '---------------tree');
      const params = {
        action: 'strategy_create',
      };
      if (node) {
        params.scope_list =  [node?.meta || {}];
      } else {
        params.all_scope =  true;
      }
      let list = await IpChooserTopo.trees(params);
      list = list.map(item => (({ ...item, lazy: !node })));
      if (node) {
        list = list.find(item => item.instance_id === node.instance_id)?.child || [];
      }
      // this.topology = list;

      return Promise.resolve(list);
    },

    // 静态拓扑 - 选中节点(根据多个拓扑节点与搜索条件批量分页查询所包含的主机信息)
    fetchTopologyHostsNodes(node = {}) {
      console.log('fetchTopologyHostsNodes', node);
      return IpChooserTopo.queryHosts({
        action: this.action,
        ...node,
      });
    },

    // 动态拓扑 - 勾选节点(查询多个节点拓扑路径)
    fetchNodesQueryPath(node: IFetchNode): Promise<Array<INode>[]> {
      console.log('fetchNodesQueryPath', node);
      return IpChooserTopo.queryPath({ action: this.action, node_list: node.node_list });
      // return node?.node_list.length
      //   ? IpChooserTopo.queryPath({ action: this.action, node_list: node.node_list })
      //   : Promise.resolve([]);
    },
    // 动态拓扑 - 勾选节点(获取多个拓扑节点的主机 Agent 状态统计信息)
    fetchHostAgentStatisticsNodes(node: IFetchNode): Promise<{ agent_statistics: IStatistics, node: INode }[]> {
      console.log('fetchHostAgentStatisticsNodes', node);
      return IpChooserTopo.agentStatistics({ action: this.action, node_list: node.node_list });
      // return node?.node_list.length
      //   ? IpChooserTopo.agentStatistics({ action: this.action, node_list: node.node_list })
      //   : Promise.resolve([]);
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
  },
  render(h) {
    return h('div', [h(this.instance, {
      ref: 'ipSelector',
      props: {
        mode: 'section',
        // service: {
        //   fetchNodesQueryPath() {} // 灰度
        // }
      },

    })]);
  },
};
