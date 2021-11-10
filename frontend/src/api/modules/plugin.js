import { request } from '../base';

export const fetchPackageInfo = request('GET', 'api/plugin/{{plugin_name}}/package/{{pk}}/');
export const fetchVersion = request('GET', 'api/plugin/{{plugin_name}}/package/fetch_version/');
export const listHost = request('POST', 'api/plugin/search/');
export const listPackage = request('GET', 'api/plugin/{{pk}}/package/');
export const listProcess = request('GET', 'api/plugin/{{pk}}/process/');
export const listProcessStatus = request('POST', 'api/plugin/process/status/');
export const operatePlugin = request('POST', 'api/plugin/operate/');
export const pluginStatistics = request('GET', 'api/plugin/statistics/');

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
