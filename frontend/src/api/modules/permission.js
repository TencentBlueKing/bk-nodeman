import { request } from '../base';

export const fetchPermission = request('POST', 'permission/fetch/');
export const listApPermission = request('GET', 'permission/ap/');
export const listCloudPermission = request('GET', 'permission/cloud/');
export const listPackagePermission = request('GET', 'permission/package/');
export const listPluginInstancePermission = request('GET', 'permission/plugin/');
export const listStartegyPermission = request('GET', 'permission/startegy/');

export default {
  fetchPermission,
  listApPermission,
  listCloudPermission,
  listPackagePermission,
  listPluginInstancePermission,
  listStartegyPermission,
};
