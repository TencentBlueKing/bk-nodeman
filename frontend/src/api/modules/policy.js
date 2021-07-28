import { request } from '../base';

export const createPolicy = request('POST', 'policy/create_policy/');
export const fetchCommonVariable = request('GET', 'policy/fetch_common_variable/');
export const fetchPolicyAbnormalInfo = request('POST', 'policy/fetch_policy_abnormal_info/');
export const fetchPolicyTopo = request('POST', 'policy/fetch_policy_topo/');
export const hostPolicy = request('GET', 'policy/host_policy/');
export const listPolicy = request('POST', 'policy/search/');
export const migratePreview = request('POST', 'policy/migrate_preview/');
export const policyInfo = request('GET', 'policy/{{pk}}/');
export const policyOperate = request('POST', 'policy/operate/');
export const policyPreselection = request('POST', 'policy/plugin_preselection/');
export const policyPreview = request('POST', 'policy/selected_preview/');
export const rollbackPreview = request('POST', 'policy/rollback_preview/');
export const updatePolicy = request('POST', 'policy/{{pk}}/update_policy/');
export const updatePolicyInfo = request('PUT', 'policy/{{pk}}/');
export const upgradePreview = request('GET', 'policy/{{pk}}/upgrade_preview/');

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
