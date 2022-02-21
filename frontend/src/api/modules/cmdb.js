import { request } from '../base';

export const fetchTopo = request('GET', 'api/cmdb/fetch_topo/');
export const retrieveBiz = request('GET', 'api/cmdb/biz/');
export const searchIp = request('GET', 'api/cmdb/search_ip/');
export const searchTopo = request('GET', 'api/cmdb/search_topo/');
export const serviceTemplate = request('GET', 'api/cmdb/service_template/');

export default {
  fetchTopo,
  retrieveBiz,
  searchIp,
  searchTopo,
};
