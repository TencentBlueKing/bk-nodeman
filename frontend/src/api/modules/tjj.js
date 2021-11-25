import { request } from '../base';

export const fetchPwd = request('POST', 'api/tjj/fetch_pwd/');

export default {
  fetchPwd,
};
