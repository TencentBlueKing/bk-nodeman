import { request } from '../base';

export const createInstallChannel = request('POST', 'install_channel/');
export const deleteInstallChannel = request('DELETE', 'install_channel/{{pk}}/');
export const listInstallChannel = request('GET', 'install_channel/');
export const updateInstallChannel = request('PUT', 'install_channel/{{pk}}/');

export default {
  createInstallChannel,
  deleteInstallChannel,
  listInstallChannel,
  updateInstallChannel,
};
