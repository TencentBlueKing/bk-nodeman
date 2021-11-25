import { request } from '../base';

export const createCloud = request('POST', 'api/cloud/');
export const deleteCloud = request('DELETE', 'api/cloud/{{pk}}/');
export const listCloud = request('GET', 'api/cloud/');
export const listCloudBiz = request('GET', 'api/cloud/{{pk}}/biz/');
export const retrieveCloud = request('GET', 'api/cloud/{{pk}}/');
export const updateCloud = request('PUT', 'api/cloud/{{pk}}/');

export default {
  createCloud,
  deleteCloud,
  listCloud,
  listCloudBiz,
  retrieveCloud,
  updateCloud,
};
