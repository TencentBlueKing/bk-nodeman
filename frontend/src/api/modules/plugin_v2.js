import { request } from '../base';

export const createExportPluginTask = request('POST', 'api/v2/plugin/create_export_task/');
export const createRegisterTask = request('POST', 'api/v2/plugin/create_register_task/');
export const fetchConfigVariables = request('POST', 'api/v2/plugin/fetch_config_variables/');
export const fetchPackageDeployInfo = request('POST', 'api/v2/plugin/fetch_package_deploy_info/');
export const listPlugin = request('GET', 'api/v2/plugin/');
export const listPluginHost = request('POST', 'api/v2/plugin/list_plugin_host/');
export const operatePlugin = request('POST', 'api/v2/plugin/operate/');
export const packageStatusOperation = request('POST', 'api/v2/plugin/package_status_operation/');
export const pluginHistory = request('GET', 'api/v2/plugin/{{pk}}/history/');
export const pluginParse = request('POST', 'api/v2/plugin/parse/');
export const pluginStatusOperation = request('POST', 'api/v2/plugin/plugin_status_operation/');
export const pluginUpload = request('POST', 'api/v2/plugin/upload/');
export const queryExportPluginTask = request('GET', 'api/v2/plugin/query_export_task/');
export const queryRegisterTask = request('GET', 'api/v2/plugin/query_register_task/');
export const retrievePlugin = request('GET', 'api/v2/plugin/{{pk}}/');
export const updatePlugin = request('PUT', 'api/v2/plugin/{{pk}}/');

export default {
  createExportPluginTask,
  createRegisterTask,
  fetchConfigVariables,
  fetchPackageDeployInfo,
  listPlugin,
  listPluginHost,
  operatePlugin,
  packageStatusOperation,
  pluginHistory,
  pluginParse,
  pluginStatusOperation,
  pluginUpload,
  queryExportPluginTask,
  queryRegisterTask,
  retrievePlugin,
  updatePlugin,
};
