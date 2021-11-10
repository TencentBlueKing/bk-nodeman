import { request } from '../base';

export const cmdbSubscription = request('POST', 'backend/api/subscription/cmdb_subscription/');
export const collectSubscriptionTaskResultDetail = request('POST', 'backend/api/subscription/collect_task_result_detail/');
export const createSubscription = request('POST', 'backend/api/subscription/create/');
export const deleteSubscription = request('POST', 'backend/api/subscription/delete/');
export const fetchCommands = request('POST', 'backend/api/subscription/fetch_commands/');
export const getGseConfig = request('POST', 'backend/get_gse_config/');
export const listDeployPolicy = request('POST', 'backend/api/subscription/search_deploy_policy/');
export const queryHostPolicy = request('GET', 'backend/api/subscription/query_host_policy/');
export const queryHostSubscriptionIds = request('GET', 'backend/api/subscription/query_host_subscriptions/');
export const queryInstanceStatus = request('POST', 'backend/api/subscription/instance_status/');
export const reportLog = request('POST', 'backend/report_log/');
export const retryNode = request('POST', 'backend/api/subscription/retry_node/');
export const retrySubscription = request('POST', 'backend/api/subscription/retry/');
export const revokeSubscription = request('POST', 'backend/api/subscription/revoke/');
export const runSubscription = request('POST', 'backend/api/subscription/run/');
export const searchPluginPolicy = request('GET', 'backend/api/subscription/search_plugin_policy/');
export const statistic = request('POST', 'backend/api/subscription/statistic/');
export const subscriptionCheckTaskReady = request('POST', 'backend/api/subscription/check_task_ready/');
export const subscriptionInfo = request('POST', 'backend/api/subscription/info/');
export const subscriptionSwitch = request('POST', 'backend/api/subscription/switch/');
export const subscriptionTaskResult = request('POST', 'backend/api/subscription/task_result/');
export const subscriptionTaskResultDetail = request('POST', 'backend/api/subscription/task_result_detail/');
export const updateSubscription = request('POST', 'backend/api/subscription/update/');

export default {
  cmdbSubscription,
  collectSubscriptionTaskResultDetail,
  createSubscription,
  deleteSubscription,
  fetchCommands,
  getGseConfig,
  listDeployPolicy,
  queryHostPolicy,
  queryHostSubscriptionIds,
  queryInstanceStatus,
  reportLog,
  retryNode,
  retrySubscription,
  revokeSubscription,
  runSubscription,
  searchPluginPolicy,
  statistic,
  subscriptionCheckTaskReady,
  subscriptionInfo,
  subscriptionSwitch,
  subscriptionTaskResult,
  subscriptionTaskResultDetail,
  updateSubscription,
};
