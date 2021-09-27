import RequestQueue from '@/api/request-queue';
import CachedPromise from '@/api/cached-promise';
import { CancelToken, Canceler } from 'axios';

export type IKeysMatch<T, V> = {[K in keyof T]-?: T[K] extends V ? K : never}[keyof T]; // 根据value类型找key

export type IAgentStatus = 'running' | 'terminated' | 'not_installed'; // 正常 异常 未安装

/* eslint-disable camelcase */
export interface ILoginData {
  width: number
  height: number
  login_url: string
  has_plain: boolean
}

export interface IAuth {
  permission: boolean
  apply_info: any
}

export interface ILoginRes {
  data: ILoginData
  config: any
  login_url: string
}

export interface IAuthApply {
  apply_info: {
    action: string
    instance_id?: number
    instance_name?: string
  }[]
}

export type RequestMethods = 'delete' | 'get' | 'head' | 'post' | 'put' | 'patch';
export type IOs = 'LINUX' | 'WINDOWS' | 'AIX';

export interface IUserConfig {
  // http 请求默认 id
  requestId?: string
  // 是否全局捕获异常
  globalError?: boolean
  // 是否直接复用缓存的请求
  fromCache?: boolean
  // 是否在请求发起前清楚缓存
  clearCache?: boolean
  // 响应结果是否返回原始数据
  originalResponse?: boolean
  // 当路由变更时取消请求
  cancelWhenRouteChange?: boolean
  // 取消上次请求
  cancelPrevious?: boolean
  cancelToken?: CancelToken
  cancelExcutor?: Canceler
}
export interface IResponse {
  config: IUserConfig
  response: any
  resolve: (value?: unknown, config?: unknown) => void
  reject: (value?: unknown) => void
}

export interface IAxiosConfig {
  hasBody?: boolean
  checkData?: boolean
  needRes?: boolean
}

export interface INodemanHttp {
  queue: RequestQueue
  cache: CachedPromise
  cancelRequest: (id: string) => Promise<any>
  cancelCache: (id: string) => Promise<any>
  cancel: (id: string) => Promise<any>
  delete?: () => Promise<any>
  get?: () => Promise<any>
  head?: () => Promise<any>
  post?: () => Promise<any>
  put?: () => Promise<any>
  patch?: () => Promise<any>
  [prop: string]: any
}

export interface INavConfig {
  title?: string // 一级导航标题
  name: string // 一级导航ID
  path?: string // 一级导航path（如果有children属性则此字段无效）
  currentActive?: string // 当前二级导航选中项
  defaultActive?: string // 当前二级导航初始化选中项
  disabled?: boolean // 是否禁用一级导航
  children?: ISubNavConfig[] // 二级导航配置
}

export interface ISubNavConfig {
  title: string // 二级导航标题
  icon: string // 二级导航icon
  path: string // 二级导航Path
  name: string // 二级导航id
  group?: boolean // 是否显示分组线
}

export interface IBkColumn {
  id: string
  label: string
  property: string
  fixed: string
  minWidth?: number
  realWidth?: number
  rowSpan?: number
  colSpan?: number
  renderHeader?: Function
  showOverflowTooltip: boolean
  sortable: boolean
  order?: null | string
  sortOrders: string[]
  resizable: boolean
  reserveSelection: boolean
  type: string

  // filterMultiple?: boolean
  // filterOpened?: boolean
  // filterPlacement?: string
  // filterSearchable?: boolean
  // filteredValue?: any[]
  // isColumnGroup?: boolean
  // level: number
  // renderCell?: Function
}

export interface IColumn {
  $index: number
  column: IBkColumn
  fixed?: boolean
  store?: any
}

export enum CheckValueEnum {
  uncheck = 0,
  indeterminate,
  checked
}

export interface IIsp {
  isp: string
  isp_icon: string
  isp_name: string
}

export interface ISearchChild {
  id: string
  name: string
  checked: boolean
}

// searchselect item
export interface ISearchItem {
  id: string
  name: string
  multiable?: boolean
  children?: ISearchChild[]
  conditions?: {
    id: string | number
    name: string
  }[]
  values?: ISearchChild[]
  width?: number
  align?: string
  showSearch?: boolean
  showCheckAll?: boolean
}

export interface ICondition {
  key: string
  value: string | Array<string | number>
}

export interface IPagination {
  limit: number
  current: number
  count: number
  limitList?: number[]
}

export type IBizValue = '' | number | number[];

export interface IBkBiz {
  bk_biz_id: number
  bk_biz_name: string
  disabled?: boolean,
  has_permission: boolean
  default?: number
  permissions?: {
    [key: string]: boolean
  }
}

// 筛选item
export interface ICheckItem {
  id: string | number
  name: string
  checked?: boolean
}

// table 设置可见列
export interface ITabelFliter {
  id: string
  name: string
  checked: boolean
  disabled: boolean
  mockChecked?: boolean
}

// export type ISetupProp = 'is_manual' | 'is_manual' | 'inner_ip' | 'outer_ip' | 'login_ip' | 'ap_id' | 'bk_biz_id' |
// 'bk_cloud_id' | 'account' | 'bt_speed_limit' | 'bt_speed_limit' | 'os_type' | 'port' | '' |
// 'peer_exchange_switch_for_agent' | 'prove' | 'retention' | 'validator'

export interface ISetupValidator {
  content: string
  show: boolean
  type: string
}

// 集合了agent 安装&导入、proxy安装
export interface ISetupRow {
  id: number
  is_manual?: boolean
  inner_ip: string
  outer_ip?: string
  login_ip?: string
  ap_id?: number
  bk_biz_id?: number
  bk_cloud_id?: number
  account?: string
  auth_type?: string
  bt_speed_limit?: string | number
  os_type?: string
  port?: number
  peer_exchange_switch_for_agent: boolean | number
  prove?: string
  retention?: number
  data_path?: string
  fileInfo?: IFileInfo
  proxyStatus?: string
  isRowValidate?: boolean
  errType?: string
  validator?: { [key: string]: ISetupValidator }
  install_channel_id: string | number | null
}
// table 表头配置
export interface ISetupHead {
  label: string
  prop: string
  reprop?: string
  subTitle?: string
  show?: boolean
  batch?: boolean
  multiple?: boolean
  default?: any
  readonly?: boolean
  required?: boolean
  noRequiredMark?: boolean
  type: string
  unique?: boolean
  union?: string
  width?: string | number
  popoverMinWidth?: number
  appendSlot?: string
  iconOffset?: number
  splitCode?: string[]
  placeholder?: string
  tips?: string
  errTag?: boolean
  rules?: any[]
  options?: any[]
  getOptions?: Function
  getReadonly?: Function
  getProxyStatus?: Function
  getCurrentType?: Function
  getDefaultValue?: Function
  handleValueChange?: Function
}

// 文件导入配置
export interface IFileInfo {
  uid: number
  name: string
  value?: string
  extension: string // 文件类型
  size: number
  status: string
  percentage: string
  errorMsg: string
  hasError: boolean
  originFile: File
  type: string
}

export interface ISortData {
  head: string
  sort_type: string
}
