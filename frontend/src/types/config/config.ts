/* eslint-disable camelcase */
export type IServerProp = 'inner_ip_infos' | 'outer_ip_infos';
export interface IIpGroup {
  inner_ip_infos: { ip: string }[]
  outer_ip_infos: { ip: string }[]

//   inner_ip: string
//   outer_ip: string
//   inner_ipv6?: string
//   outer_ipv6?: string
}


export interface IZk {
  zk_ip: string
  zk_port: string
}

interface IConfigPort {
  [key: string]: number
}
interface IApAuth {
  delete: boolean
  edit: boolean
  view: boolean
}
// enum IApAuth {
//   delete = 'delete',
//   edit = 'edit',
//   view = 'view'
// }

export interface IConfigAgent {
  linux: { [key: string]: string }
  windows: { [key: string]: string }
}

export interface IApBase {
  name: string
  zk_account: string
  zk_password?: string // 编辑可不填
  zk_hosts: IZk[]
  city_id: string
  region_id: string
  btfileserver: IIpGroup
  dataserver: IIpGroup
  taskserver: IIpGroup
  description: string
  callback_url: string
  outer_callback_url: string
  package_inner_url: string
  package_outer_url: string
  nginx_path: null | ''
  gse_version?: 'V1' | 'V2' // ENABLE_AP_VERSION_MUTEX 开启时使用
}

export interface IApParams extends IApBase {
  agent_config: IConfigAgent
  proxy_package: string[]
  pwsFill?: boolean
}
export interface IAp extends IApParams {
  id: number
  permissions: IApAuth
  port_config?: IConfigPort

  ap_type: string
  is_enabled: boolean
  is_default: boolean
  file_cache_dirs: string
  // nginx_path: null | string
}

export interface IApExpand extends IAp {
  BtfileServer: IIpGroup;
  DataServer: IIpGroup;
  TaskServer: IIpGroup;
  is_used?: boolean;
  // is_default?: boolean;
  collapse: boolean;
  linux: { name: TranslateResult; value: string; }[];
  windows: { name: TranslateResult; value: string; }[];
  view?: boolean;
}

export interface ITaskConfig {
  install_p_agent_timeout: number
  install_agent_timeout: number
  install_proxy_timeout: number,
  install_download_limit_speed: number
  parallel_install_number: number
  node_man_log_level: string

}

// server 可用性
export interface IAvailable {
  btfileserver: IIpGroup
  dataserver: IIpGroup
  taskserver: IIpGroup
  package_inner_url: string
  package_outer_url: string
  callback_url?: string
  outer_callback_url?: string
}
