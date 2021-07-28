import { request } from '../base';

export const createExportPluginTask = request('POST', 'plugin/create_export_task/');
export const createPluginConfigTemplate = request('POST', 'plugin/create_config_template/');
export const createRegisterTask = request('POST', 'plugin/create_register_task/');
export const deletePlugin = request('POST', 'plugin/delete/');
export const downloadContent = request('GET', 'export/download/');
export const listPlugin = request('GET', 'plugin/');
export const packageStatusOperation = request('POST', 'plugin/package_status_operation/');
export const pluginHistory = request('GET', 'plugin/{{pk}}/history/');
export const pluginParse = request('POST', 'plugin/parse/');
export const pluginStatusOperation = request('POST', 'plugin/plugin_status_operation/');
export const queryDebug = request('GET', 'plugin/query_debug/');
export const queryExportPluginTask = request('GET', 'plugin/query_export_task/');
export const queryPluginConfigInstance = request('GET', 'plugin/query_config_instance/');
export const queryPluginConfigTemplate = request('GET', 'plugin/query_config_template/');
export const queryPluginInfo = request('GET', 'plugin/info/');
export const queryRegisterTask = request('GET', 'plugin/query_register_task/');
export const releasePackage = request('POST', 'plugin/release/');
export const releasePluginConfigTemplate = request('POST', 'plugin/release_config_template/');
export const renderPluginConfigTemplate = request('POST', 'plugin/render_config_template/');
export const retrievePlugin = request('GET', 'plugin/{{pk}}/');
export const startDebug = request('POST', 'plugin/start_debug/');
export const stopDebug = request('POST', 'plugin/stop_debug/');
export const uploadFile = request('POST', 'package/upload/');

export default {
  createExportPluginTask,
  createPluginConfigTemplate,
  createRegisterTask,
  deletePlugin,
  downloadContent,
  listPlugin,
  packageStatusOperation,
  pluginHistory,
  pluginParse,
  pluginStatusOperation,
  queryDebug,
  queryExportPluginTask,
  queryPluginConfigInstance,
  queryPluginConfigTemplate,
  queryPluginInfo,
  queryRegisterTask,
  releasePackage,
  releasePluginConfigTemplate,
  renderPluginConfigTemplate,
  retrievePlugin,
  startDebug,
  stopDebug,
  uploadFile,
};
