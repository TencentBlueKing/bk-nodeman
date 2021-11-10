import { request } from '../base';

export const createPolicy = request('POST', 'api/policy/create_policy/');
export const fetchCommonVariable = request('GET', 'api/policy/fetch_common_variable/');
export const fetchPolicyAbnormalInfo = request('POST', 'api/policy/fetch_policy_abnormal_info/');
export const fetchPolicyTopo = request('POST', 'api/policy/fetch_policy_topo/');
export const hostPolicy = request('GET', 'api/policy/host_policy/');
export const listPolicy = request('POST', 'api/policy/search/');
export const migratePreview = request('POST', 'api/policy/migrate_preview/');
export const policyInfo = request('GET', 'api/policy/{{pk}}/');
export const policyOperate = request('POST', 'api/policy/operate/');
export const policyPreselection = request('POST', 'api/policy/plugin_preselection/');
export const policyPreview = request('POST', 'api/policy/selected_preview/');
export const rollbackPreview = request('POST', 'api/policy/rollback_preview/');
export const updatePolicy = request('POST', 'api/policy/{{pk}}/update_policy/');
export const updatePolicyInfo = request('PUT', 'api/policy/{{pk}}/');
export const upgradePreview = request('GET', 'api/policy/{{pk}}/upgrade_preview/');

export default {
  createPolicy,
  fetchCommonVariable,
  fetchPolicyAbnormalInfo,
  fetchPolicyTopo,
  hostPolicy,
  listPolicy,
  migratePreview,
  policyInfo,
  policyOperate,
  policyPreselection,
  policyPreview,
  rollbackPreview,
  updatePolicy,
  updatePolicyInfo,
  upgradePreview,
};
