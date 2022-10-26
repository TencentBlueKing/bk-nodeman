import { request } from '../base';

export const check = request('POST', 'core/api/ipchooser_host/check/');
export const details = request('POST', 'core/api/ipchooser_host/details/');

export default {
  check,
  details,
};
