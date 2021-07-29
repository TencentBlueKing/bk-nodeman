import { request } from '../base';

export const healthz = request('GET', 'healthz/');

export default {
  healthz,
};
