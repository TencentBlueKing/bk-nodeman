import { request } from '../base';

export const trees = request('POST', 'core/api/ipchooser_topo/trees/');
export const queryPath = request('POST', 'core/api/ipchooser_topo/query_path/');
export const queryHosts = request('POST', 'core/api/ipchooser_topo/query_hosts/');
export const queryHostIdInfos = request('POST', 'core/api/ipchooser_topo/query_host_id_infos/');
export const agentStatistics = request('POST', 'core/api/ipchooser_topo/agent_statistics/');

export default {
  trees,
  queryPath,
  queryHosts,
  queryHostIdInfos,
  agentStatistics,
};
