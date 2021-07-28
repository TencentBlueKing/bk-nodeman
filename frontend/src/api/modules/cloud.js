import { request } from '../base';

export const createCloud = request('POST', 'cloud/');
export const deleteCloud = request('DELETE', 'cloud/{{pk}}/');
export const listCloud = request('GET', 'cloud/');
export const listCloudBiz = request('GET', 'cloud/{{pk}}/biz/');
export const retrieveCloud = request('GET', 'cloud/{{pk}}/');
export const updateCloud = request('PUT', 'cloud/{{pk}}/');

export default {
  createCloud,
  deleteCloud,
  listCloud,
  listCloudBiz,
  retrieveCloud,
  updateCloud,
};
