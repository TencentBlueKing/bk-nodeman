import { request } from '../base';

export const listHost = request('POST', 'api/host/search/');
export const removeHost = request('POST', 'api/host/remove_host/');
export const retrieveBizProxies = request('GET', 'api/host/biz_proxies/');
export const retrieveCloudProxies = request('GET', 'api/host/proxies/');
export const updateHost = request('POST', 'api/host/update_single/');

export default {
  listHost,
  removeHost,
  retrieveBizProxies,
  retrieveCloudProxies,
  updateHost,
};
