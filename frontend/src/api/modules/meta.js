import { request } from '../base';

export const getFilterCondition = request('GET', 'meta/filter_condition/');
export const jobSettings = request('POST', 'meta/job_settings/');
export const retrieveGlobalSettings = request('GET', 'meta/global_settings/');

export default {
  getFilterCondition,
  jobSettings,
  retrieveGlobalSettings,
};
