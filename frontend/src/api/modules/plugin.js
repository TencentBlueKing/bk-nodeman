import { request } from '../base';

export const fetchPackageInfo = request('GET', 'plugin/{{plugin_name}}/package/{{pk}}/');
export const fetchVersion = request('GET', 'plugin/{{plugin_name}}/package/fetch_version/');
export const listHost = request('POST', 'plugin/search/');
export const listPackage = request('GET', 'plugin/{{pk}}/package/');
export const listProcess = request('GET', 'plugin/{{pk}}/process/');
export const listProcessStatus = request('POST', 'plugin/process/status/');
export const operatePlugin = request('POST', 'plugin/operate/');
export const pluginStatistics = request('GET', 'plugin/statistics/');

export default {
  fetchPackageInfo,
  fetchVersion,
  listHost,
  listPackage,
  listProcess,
  listProcessStatus,
  operatePlugin,
  pluginStatistics,
};
