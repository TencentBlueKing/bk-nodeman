import { request } from '../base';

export const fetchPwd = request('POST', 'tjj/fetch_pwd/');

export default {
  fetchPwd,
};
