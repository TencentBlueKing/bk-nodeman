import { request } from '../base';

export const createExportPluginTask = request('POST', 'backend/api/plugin/create_export_task/');
export const createPluginConfigTemplate = request('POST', 'backend/api/plugin/create_config_template/');
export const createRegisterTask = request('POST', 'backend/api/plugin/create_register_task/');
export const deletePlugin = request('POST', 'backend/api/plugin/delete/');
export const downloadContent = request('GET', 'backend/export/download/');
export const listPlugin = request('GET', 'backend/api/plugin/');
export const packageStatusOperation = request('POST', 'backend/api/plugin/package_status_operation/');
export const pluginHistory = request('GET', 'backend/api/plugin/{{pk}}/history/');
export const pluginParse = request('POST', 'backend/api/plugin/parse/');
export const pluginStatusOperation = request('POST', 'backend/api/plugin/plugin_status_operation/');
export const queryDebug = request('GET', 'backend/api/plugin/query_debug/');
export const queryExportPluginTask = request('GET', 'backend/api/plugin/query_export_task/');
export const queryPluginConfigInstance = request('GET', 'backend/api/plugin/query_config_instance/');
export const queryPluginConfigTemplate = request('GET', 'backend/api/plugin/query_config_template/');
export const queryPluginInfo = request('GET', 'backend/api/plugin/info/');
export const queryRegisterTask = request('GET', 'backend/api/plugin/query_register_task/');
export const releasePackage = request('POST', 'backend/api/plugin/release/');
export const releasePluginConfigTemplate = request('POST', 'backend/api/plugin/release_config_template/');
export const renderPluginConfigTemplate = request('POST', 'backend/api/plugin/render_config_template/');
export const retrievePlugin = request('GET', 'backend/api/plugin/{{pk}}/');
export const startDebug = request('POST', 'backend/api/plugin/start_debug/');
export const stopDebug = request('POST', 'backend/api/plugin/stop_debug/');
export const upload = request('POST', 'backend/api/plugin/upload/');
export const uploadFile = request('POST', 'backend/package/upload/');

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
  upload,
  uploadFile,
};
