import { request } from '../base';

export const listHost = request('POST', 'host/search/');
export const removeHost = request('POST', 'host/remove_host/');
export const retrieveBizProxies = request('GET', 'host/biz_proxies/');
export const retrieveCloudProxies = request('GET', 'host/proxies/');
export const updateHost = request('POST', 'host/update_single/');

export default {
  listHost,
  removeHost,
  retrieveBizProxies,
  retrieveCloudProxies,
  updateHost,
};
