import { request } from '../base';

export const healthz = request('GET', 'api/healthz/');

export default {
  healthz,
};
