import { request } from '../base';

export const listCategory = request('GET', 'choice/category/');
export const listJobType = request('GET', 'choice/job_type/');
export const listOp = request('GET', 'choice/op/');
export const listOsType = request('GET', 'choice/os_type/');

export default {
  listCategory,
  listJobType,
  listOp,
  listOsType,
};
