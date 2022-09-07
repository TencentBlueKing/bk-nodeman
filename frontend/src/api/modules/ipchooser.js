import { request } from '../base';

export const ipChooserHostCheck = request('POST', '/core/api/ipchooser_host/check/'); // 根据用户手动输入的`ip`/`ipv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息 core_api_ipchooser_host_check"
export const ipChooserHostDetails = request('POST', '/core/api/ipchooser_host/details/'); // 根据主机关键信息获取机器详情信息 core_api_ipchooser_host_details"
export const ipChooserTopoAgentStatistics = request('POST', '/core/api/ipchooser_topo/agent_statistics/'); // 获取多个拓扑节点的主机 agent"
export const ipChooserTopoQueryHostIdInfos = request('POST', '/core/api/ipchooser_topo/query_host_id_infos/'); // 根据多个拓扑节点与搜索条件批量分页查询所包含的主机 id"
export const ipChooserTopoQueryHosts = request('POST', '/core/api/ipchooser_topo/query_hosts/'); // 根据多个拓扑节点与搜索条件批量分页查询所包含的主机信息 core_api_ipchooser_topo_query_hosts"
export const ipChooserTopoQueryPath = request('POST', '/core/api/ipchooser_topo/query_path/'); // 查询多个节点拓扑路径 core_api_ipchooser_topo_query_path"
export const ipChooserTopoTrees = request('POST', '/core/api/ipchooser_topo/trees/'); // 批量获取含各节点主机数量的拓扑树 core_api_ipchooser_topo_trees"

export default {
  ipChooserHostCheck,
  ipChooserHostDetails,
  ipChooserTopoAgentStatistics,
  ipChooserTopoQueryHostIdInfos,
  ipChooserTopoQueryHosts,
  ipChooserTopoQueryPath,
  ipChooserTopoTrees,
};
