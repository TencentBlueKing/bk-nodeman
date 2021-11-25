import { request } from '../base';

export const fetchPermission = request('POST', 'api/permission/fetch/');
export const listApPermission = request('GET', 'api/permission/ap/');
export const listCloudPermission = request('GET', 'api/permission/cloud/');
export const listPackagePermission = request('GET', 'api/permission/package/');
export const listPluginInstancePermission = request('GET', 'api/permission/plugin/');
export const listStartegyPermission = request('GET', 'api/permission/startegy/');

export default {
  fetchPermission,
  listApPermission,
  listCloudPermission,
  listPackagePermission,
  listPluginInstancePermission,
  listStartegyPermission,
};
