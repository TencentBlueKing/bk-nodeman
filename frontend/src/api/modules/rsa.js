import { request } from '../base';

export const fetchPublicKeys = request('POST', 'core/api/encrypt_rsa/fetch_public_keys/');

export default {
  fetchPublicKeys,
};
