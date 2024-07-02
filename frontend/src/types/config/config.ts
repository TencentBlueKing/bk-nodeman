/* eslint-disable camelcase */
export interface IIpGroup {
  inner_ip: string
  outer_ip: string
  inner_ipv6?: string
  outer_ipv6?: string
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
  btfileserver: IIpGroup[]
  dataserver: IIpGroup[]
  taskserver: IIpGroup[]
  description: string
  callback_url: string
  outer_callback_url: string
  package_inner_url: string
  package_outer_url: string
  nginx_path: null | ''
  gse_version: 'V1' | 'V2' // ENABLE_AP_VERSION_MUTEX 开启时使用
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
  BtfileServer: IIpGroup[]
  DataServer: IIpGroup[]
  TaskServer: IIpGroup[]
  is_used?: boolean
  // is_default?: boolean
  collapse: boolean
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
  btfileserver: IIpGroup[]
  dataserver: IIpGroup[]
  taskserver: IIpGroup[]
  package_inner_url: string
  package_outer_url: string
  callback_url?: string
  outer_callback_url?: string
}

// 平台信息配置
export interface IPlatformConfig {
  bkAppCode: string, // appcode
  name: string, // 站点的名称，通常显示在页面左上角，也会出现在网页title中
  nameEn: string, // 站点的名称-英文
  appLogo: string, // 站点logo
  favicon: string, // 站点favicon
  helperText: string,
  helperTextEn: string,
  helperLink: string,
  brandImg: string,
  brandImgEn: string,
  brandName: string, // 品牌名，会用于拼接在站点名称后面显示在网页title中
  favIcon: string,
  brandNameEn: string, // 品牌名-英文
  footerInfo: string, // 页脚的内容，仅支持 a 的 markdown 内容格式
  footerInfoEn: string, // 页脚的内容-英文
  footerCopyright: string, // 版本信息，包含 version 变量，展示在页脚内容下方

  footerInfoHTML: string,
  footerInfoHTMLEn: string,
  footerCopyrightContent: string,
  version: string,

  // 需要国际化的字段，根据当前语言cookie自动匹配，页面中应该优先使用这里的字段
  i18n: {
    name: string,
    helperText: string,
    brandImg: string,
    brandName: string,
    footerInfoHTML: string,
  },
};
