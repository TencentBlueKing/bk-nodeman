import { request } from '../base';

export const listPackage = request('GET', 'api/agent/package/');
export const updatePackage = request('PUT', 'api/agent/package/{{pk}}/');
export const deletePackage = request('DELETE', 'api/agent/package/{{pk}}/');
export const quickSearchCondition = request('GET', 'api/agent/package/quick_search_condition/');
export const uploadPackage = request('POST', 'api/agent/package/upload/');
export const parsePackage = request('POST', 'api/agent/package/parse/');
export const createAgentRegisterTask = request('POST', 'api/agent/package/create_register_task/');
export const queryAgentRegisterTask = request('GET', 'api/agent/package/query_register_task/');
export const getTags = request('GET', 'api/agent/package/tags/');
export const getVersion = request('POST', 'api/agent/package/version/');
export const getDeployedHostsCount = request('POST', 'api/agent/package/deployed_hosts_count/');
export const createAgentTags = request('POST', 'api/agent/package/create_agent_tags/');
export const versionCompare = request('POST', 'api/agent/package/version_compare/');

export default {
  listPackage,
  updatePackage,
  deletePackage,
  quickSearchCondition,
  uploadPackage,
  parsePackage,
  createAgentRegisterTask,
  queryAgentRegisterTask,
  getTags,
  getVersion,
  getDeployedHostsCount,
  createAgentTags,
  versionCompare,
};
