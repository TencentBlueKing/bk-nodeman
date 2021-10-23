import { request } from '../base';

export const cmdbSubscription = request('POST', 'subscription/cmdb_subscription/');
export const collectSubscriptionTaskResultDetail = request('POST', 'subscription/collect_task_result_detail/');
export const createSubscription = request('POST', 'subscription/create/');
export const deleteSubscription = request('POST', 'subscription/delete/');
export const fetchCommands = request('POST', 'subscription/fetch_commands/');
export const getGseConfig = request('POST', 'get_gse_config/');
export const listDeployPolicy = request('POST', 'subscription/search_deploy_policy/');
export const queryHostPolicy = request('GET', 'subscription/query_host_policy/');
export const queryHostSubscriptionIds = request('GET', 'subscription/query_host_subscriptions/');
export const queryInstanceStatus = request('POST', 'subscription/instance_status/');
export const reportLog = request('POST', 'report_log/');
export const retryNode = request('POST', 'subscription/retry_node/');
export const retrySubscription = request('POST', 'subscription/retry/');
export const revokeSubscription = request('POST', 'subscription/revoke/');
export const runSubscription = request('POST', 'subscription/run/');
export const searchPluginPolicy = request('GET', 'subscription/search_plugin_policy/');
export const statistic = request('POST', 'subscription/statistic/');
export const subscriptionCheckTaskReady = request('POST', 'subscription/check_task_ready/');
export const subscriptionInfo = request('POST', 'subscription/info/');
export const subscriptionSwitch = request('POST', 'subscription/switch/');
export const subscriptionTaskResult = request('POST', 'subscription/task_result/');
export const subscriptionTaskResultDetail = request('POST', 'subscription/task_result_detail/');
export const updateSubscription = request('POST', 'subscription/update/');

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
