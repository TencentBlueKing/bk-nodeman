import { request } from '../base';

export const getFilterCondition = request('GET', 'api/meta/filter_condition/');
export const jobSettings = request('POST', 'api/meta/job_settings/');
export const retrieveGlobalSettings = request('GET', 'api/meta/global_settings/');

export default {
  getFilterCondition,
  jobSettings,
  retrieveGlobalSettings,
};
