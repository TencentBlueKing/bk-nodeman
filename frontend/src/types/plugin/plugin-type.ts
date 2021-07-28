/* eslint-disable camelcase */
import { TranslateResult } from 'vue-i18n';

export interface IPanel {
  name: string
  label: string | TranslateResult,
  data?: any[]
}

export type PkgOperateType = 'online' | 'offline' | 'verifying' | 'download';

export interface IHostOperate {
  id: string
  name: TranslateResult
}
export interface ISearchParams {
  page?: number
  pagesize: number
  conditions: ICondition[],
  bk_biz_id?: number[]
  simple?: boolean
  sort?: {
    head: string
    sort_type: string
  }
}

export interface IHostData {
  total: number
  list: IPluginList[]
}

export interface ICondition {
  key: string | number
  value: string | number | (string | number)[]
}

export interface ITask {
  name: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'unknown'
  id: string | number
}

export interface ISubscriptionStatistics {
  not_installed: number
  running: number
  terminated: number
  unknown: number
}

export interface IPluginStatus {
  name: string
  status: string
  version: string
  // subscription_statistics: ISubscriptionStatistics
  // subscription_tasks: ITask[]
}

export interface IMenu {
  id: string | number
  name: string | TranslateResult
  disabled?: boolean
}

/**
 * 节点列表
 */
export interface IPluginTopo {
  id: number | string
  name: string
  type: string
  key?: number | string
  children?: IPluginTopo[]
}

export interface IPluginList {
  bk_host_id: number
  inner_ip: string
  plugin_status: IPluginStatus[]
  selection: boolean
  status: 'RUNNING' | 'TERMINATED' | 'UNKNOWN' | 'UNREGISTER'
  version: string
  bk_cloud_id: number
  bk_cloud_name: string
  bk_biz_id: number
  bk_biz_name: string
  node_type: string
  os_type: string
  node_from: string
  status_display: string
  job_result: any
}

/**
 * 部署策略
 */
export interface IChoosePlugin {
  id: number
  name: string
  label?: string
  description: string
}

interface IBizScope {
  bk_biz_id: number
  bk_biz_name: string
}
export interface IPolicyBase {
  id: number
  name: string
  plugin_name: string
  plugin_id: number
  bk_biz_scope: IBizScope[]
  associated_host_num: number
  permissions?: Dictionary
  enable?: boolean
  job_result: Dictionary
  configs: IPk[]
  // creator: string
  // update_time: string
}
export interface IPolicyRow extends IPolicyBase {
  hasGrayRule: boolean
  expand: boolean
  isGrayRule?: boolean
  pid?: number
  compare_with_root?: number
  children: IPolicyRow[]
  abnormal_host_count?: number
  abnormal_host_ids?: number[]
}


export interface IRuleType {
  icon: string
  title: string | TranslateResult
  desc: string | TranslateResult
  tips?: string | TranslateResult
  disabled: boolean
  id: string
}

export interface IStep {
  title: string | TranslateResult
  icon: number
  description?: string
  com: string,
  disabled?: boolean
  error?: boolean
}

export interface IRule {
  required?: boolean
  message: string | TranslateResult
  trigger: 'blur' | 'change'
  min?: number
  max?: number
}

export interface INode {
  id: string | number
  name: string | TranslateResult
  children?: INode[]
  index?: number
  parent?: INode
}

export interface ITarget {
  // node_type = 'INSTANCE' => bk_host_id  ||  'TOPO' => bk_obj_id && bk_inst_id
  bk_biz_id: number,
  bk_obj_id?: 'set' | 'module'
  bk_inst_id?: number
  bk_host_id?: number
  biz_inst_id?: string
  path?: string
  children?: ITarget[]
}

export interface IParamsData {
  prop: string
  type: 'string' | 'number',
  label?: string | TranslateResult
  required: boolean
  disabled?: boolean
  copy?: boolean
  default?: string | number
  restore?: boolean
  rules?: IRule[]
  inputName?: string
}

export interface IParamsChild {
  title: string
  version: string
  name: string
  is_main: boolean
  form: Dictionary
  data: IParamsData[]
  inputName?: string
}

// 参数配置 - item
export interface IParamsConfig extends IPk {
  title: string
  version: string
  name?: string
  plugin_name?: string
  form: Dictionary
  data: IParamsData[]
  os: string,
  child?: IParamsChild[]
  childActive: string[]
  defaultActive: string[]
  is_main?: boolean
  // inputName?: string

  // config_templates:Array[1]
  // cpu_arch: string
  // creator: string
  // disabled: boolean
  // id: number
  // is_ready: boolean
  // is_release_version:true
  // md5:"e0ba1cf6a9835de3c470e2ea58dafca0"
  // module:"gse_plugin"
  // pkg_mtime:"2020-09-25 06:53:10.961393+00:00"
  // pkg_name:"processbeat-1.10.32.tgz"
  // pkg_size:4164150
  // project:"processbeat"
  // selection:false
}

export interface IPkConfig {
  cpu_arch: string
  os_type: string
  child?: {
    [key: number]: Dictionary
  }[]
}

export interface IPkConfigDetail {
  id: number
  type?: 'PLUGIN' | 'AGENT'
  configs: { details: IPk[] }
  params: IPkConfig[]
}

export interface IStrategy { // 与策略列表不通用
  plugin_info?: {
    id: string | number
    name: string
  }
  name?: string
  subscription_id?: number | string
  scope: {
    object_type?: 'HOST' | 'SERVICE'
    node_type: 'TOPO' | 'INSTANCE'
    nodes: ITarget[]
  }
  steps: IPkConfigDetail[]
  configs?: IPk[] // steps-扁平化
  params?: {
    cpu_arch: string
    os_type: string
    context: Dictionary
    child?: Dictionary
  }[] // steps-扁平化
}

export interface IPluginRuleParams {
  page: number
  pagesize: number
  bk_biz_ids?: number[]
  conditions?: any[]
  only_root?: boolean
}

// 升级版本 - 待定
export interface IVersionRow {
  os: string
  cpu_arch: string
  current_version: string
  is_latest: boolean
  latest_version: string
  nodes_number: number
  version_scenario: string
  selectedVersion: string
  checked: boolean
  disabled?: boolean
  versionTarget?: IPkVersionRow
  support_os_cpu?: string
  rowspan?: number
}

export interface IPreviewHost {
  bk_biz_id: number
  bk_biz_name: string
  bk_cloud_id: number
  bk_cloud_name: string
  bk_host_id: number
  inner_ip: string
  os_type: string
  osType?: string
  status: string
  statusDisplay?: string
  version?: string
  current_version?: string
  target_version?: string
}

// export interface IPreviewNode {
//   id: number
//   biz_inst_id: string
//   bk_biz_id: number
//   bk_inst_id: number
//   bk_obj_id: string
//   path: string
//   type: string
// }
// export interface IPolicyPreview {

// }
export interface IPolicyOperate {
  job_id?: number
  deleted?: boolean
  subscription_id?: number
}

/*
 * 插件包相关
 */
export interface IPluginRow {
  id: number
  name: string
  category: string
  deploy_type: string
  description: string
  nodes_number: number
  scenario: string
  source_app_code: string
  is_ready?: boolean,
  permissions?: {
    [key: string]: boolean
  }
}

// config_templates
export interface IPkConfigTemplate {
  id: number
  is_main: boolean
  name:  string
  plugin_version: string
  version: string
}

export interface IPk {
  id: number
  pkg_name: string
  pkg_mtime: string
  cpu_arch: string
  os: string
  module: string
  creator: string
  is_ready: boolean
  project: string
  support_os_cpu: string
  version: string
  mainConfigVersion?: string
  childConfigTemplates?: IPkConfigTemplate[]
  config_templates: IPkConfigTemplate[]
  operateLoading?: boolean
}

export interface IPkVersionRow extends IPk {
  disabled?: boolean
  isBelowVersion?: boolean
  is_newest: boolean
  is_release_version: boolean
  md5: string
  pkg_size: number
}

export interface IPluginDetail extends IPluginRow {
  plugin_packages: IPk[]
  disabled?: boolean
  selection?: boolean
  is_ready?: boolean
  operate?: boolean // 可操作权限
}

export interface IPluginInfoConfig {
  id: string
  name: string | TranslateResult
  value: string
}

export interface IPkParseRow extends IPk {
  pkg_abs_path: string
  result?: boolean
}
