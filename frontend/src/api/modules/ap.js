import { request } from '../base';

export const apIsUsing = request('get', 'ap/ap_is_using/');
export const createAp = request('POST', 'ap/');
export const deleteAp = request('DELETE', 'ap/{{pk}}/');
export const initPluginData = request('POST', 'ap/init_plugin/');
export const listAp = request('GET', 'ap/');
export const retrieveAp = request('GET', 'ap/{{pk}}/');
export const testAp = request('POST', 'ap/test/');
export const updateAp = request('PUT', 'ap/{{pk}}/');

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
