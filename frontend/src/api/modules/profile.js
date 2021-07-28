import { request } from '../base';

export const listProfile = request('GET', 'profile/');
export const updateOrCreateProfile = request('POST', 'profile/update_or_create/');

export default {
  listProfile,
  updateOrCreateProfile,
};
