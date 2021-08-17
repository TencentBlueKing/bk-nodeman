/* eslint-disable camelcase */
export interface ICloudAuth {
  edit_action?: number[]
  delete_action?: number[]
  create_action?: boolean
  view_action?: number[]
  proxy_operate?: any[]
}
export interface ICloudListAuth {
  view?: boolean
  edit?: boolean
  delete?: boolean
}
export interface IIpGroup {
  inner_ip: string
  outer_ip: string
}
export interface ICloudForm {
  bk_cloud_name: string
  isp: string
  ap_id?: number
}

export interface ICloud {
  apId: number
  apName: string
  bkCloudId: number
  bkCloudName: string
  exception: string
  isVisible?: boolean
  isp: string
  ispIcon: string
  ispName: string
  nodeCount: number
  permissions?: ICloudListAuth
  proxies?: IIpGroup[]
  proxyCount: number
  cloudNameCopy?: string
  view?: boolean
  edit?: boolean
  delete?: boolean
}
export interface ICloudSource {
  ap_id: number
  ap_name: string
  bk_cloud_id: number
  bk_cloud_name: string
  exception: string
  is_visible?: boolean
  isp: string
  isp_icon: string
  isp_name: string
  node_count?: number
  permissions?: { view: boolean, edit: boolean, delete: boolean }
  proxies: IIpGroup[]
  proxy_count: number
  view?: boolean
  edit?: boolean
  delete?: boolean
  bk_biz_scope?: number[]
}
export interface IProxyDetail {
  ap_id: number
  ap_name: string
  bk_biz_id: number
  bk_biz_name: string
  bk_cloud_id: number
  bk_host_id: number
  data_ip: string
  inner_ip: string
  login_ip: string
  outer_ip: string

  is_manual?: boolean
  port?: number
  auth_type?: string
  bt_speed_limit?: number
  peer_exchange_switch_for_agent: boolean
  re_certification: boolean
  extra_data?: any
  account?: string
  pagent_count?: number
  job_result?: any
  status?: string
  status_display?: string
  version?: string
}

export interface IChannel {
  id: number | string
  name: string
  bk_cloud_id: number
  jump_servers: string[]
  upstream_servers: { [key: string]: string[] }
}
