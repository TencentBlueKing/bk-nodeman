import { request } from '../base';

export const fetchTopo = request('GET', 'cmdb/fetch_topo/');
export const retrieveBiz = request('GET', 'cmdb/biz/');
export const searchIp = request('GET', 'cmdb/search_ip/');
export const searchTopo = request('GET', 'cmdb/search_topo/');

export default {
  fetchTopo,
  retrieveBiz,
  searchIp,
  searchTopo,
};
