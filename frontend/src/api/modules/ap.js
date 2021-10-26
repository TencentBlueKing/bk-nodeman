import { request } from '../base';

export const apIsUsing = request('get', 'api/ap/ap_is_using/');
export const createAp = request('POST', 'api/ap/');
export const deleteAp = request('DELETE', 'api/ap/{{pk}}/');
export const initPluginData = request('POST', 'api/ap/init_plugin/');
export const listAp = request('GET', 'api/ap/');
export const retrieveAp = request('GET', 'api/ap/{{pk}}/');
export const testAp = request('POST', 'api/ap/test/');
export const updateAp = request('PUT', 'api/ap/{{pk}}/');

export default {
  apIsUsing,
  createAp,
  deleteAp,
  initPluginData,
  listAp,
  retrieveAp,
  testAp,
  updateAp,
};
