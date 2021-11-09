import { request } from '../base';

export const createInstallChannel = request('POST', 'api/install_channel/');
export const deleteInstallChannel = request('DELETE', 'api/install_channel/{{pk}}/');
export const listInstallChannel = request('GET', 'api/install_channel/');
export const updateInstallChannel = request('PUT', 'api/install_channel/{{pk}}/');

export default {
  createInstallChannel,
  deleteInstallChannel,
  listInstallChannel,
  updateInstallChannel,
};
