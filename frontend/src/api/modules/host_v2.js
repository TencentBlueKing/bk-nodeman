import { request } from '../base';

export const listHost = request('POST', 'v2/host/search/');
export const nodeStatistic = request('POST', 'v2/host/node_statistic/');
export const nodesAgentStatus = request('POST', 'v2/host/agent_status/');

export default {
  listHost,
  nodeStatistic,
  nodesAgentStatus,
};
