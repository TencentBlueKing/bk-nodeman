import { request } from '../base';

export const getFilterCondition = request('POST', 'api/meta/filter_condition/');
export const jobSettings = request('POST', 'api/meta/job_settings/');
export const retrieveGlobalSettings = request('GET', 'api/meta/global_settings/');
// agent_package开关
export const getAgentPackageUI = request('GET', 'api/meta/global_settings');

export default {
  getFilterCondition,
  jobSettings,
  retrieveGlobalSettings,
  getAgentPackageUI,
};
