import RequestQueue from '@/api/request-queue';
import CachedPromise from '@/api/cached-promise';
import { CancelToken, Canceler } from 'axios';

export type Mixin<T, X> = T & X;

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
export type IOs = 'LINUX' | 'WINDOWS' | 'AIX' | 'SOLARIS';
export type IProxyIpKeys = 'inner_ip' | 'outer_ip' | 'login_ip';

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
  get?: (url: string) => Promise<any>
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
  children?: ISideMenuCofig[] // 二级导航配置
}

// 侧边栏菜单配置
export interface ISideMenuCofig {
  name: string // 侧边栏菜单分类名称
  children?: ISubNavConfig[] // 子菜单配置
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
  checked?: boolean
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
  mockChecked?: boolean,
  filter?: boolean
  sort?: boolean
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
  inner_ip?: string
  outer_ip?: string
  login_ip?: string
  inner_ipv6?: string
  outer_ipv6?: string
  login_ipv6?: string
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
  password?: string
  key?: string
  retention?: number
  data_path?: string
  fileInfo?: IFileInfo
  proxyStatus?: string
  isRowValidate?: boolean
  errType?: string
  validator?: { [key: string]: ISetupValidator }
  install_channel_id: string | number | null
  bk_addressing: 'static' | 'dynamic'
  gse_version?: 'V1'|'V2' // 前端添加 用于操作主机仅能选择对应版本的接入点
  bk_host_id?: number;
  version?: string;
}

export interface ISetupParent {
  label: string
  prop: string
  type?: string
  tips?: string
  colspan?: number
}

// table 表头配置
export interface ISetupHead {
  label: string
  prop: string
  reprop?: string // textarea 多IP与另一字段一一对应
  parentProp?: string // 二级表头归类到一级表头下的prop
  parentTip?: string // 一级表头tooltips
  subTitle?: string // 二级表头tooltips
  show?: boolean
  batch?: boolean // 可批量修改
  sync?: string // 当前值同步到另一字段
  multiple?: boolean // 可多选 - 下拉框
  default?: any // 默认值
  readonly?: boolean
  required?: boolean // 必填校验
  requiredPick?: string[] // 必填多选一
  noRequiredMark?: boolean // 必填*号
  type: string
  unique?: boolean // IP行内和其他行的重复性校验
  union?: string // 相同ip时联合管控区域做校验（允许不同管控区域时IP相同）
  width?: string | number
  minWidth?: string | number
  popoverMinWidth?: number
  // appendSlot?: string // head单位
  iconOffset?: number
  splitCode?: string[]
  placeholder?: string
  tips?: string
  errTag?: boolean // cell右上角冲突标记
  rules?: any[]
  options?: any[]
  manualProp?: boolean // 手动安装需要的配置
  getOptions?: Function // row 为{}时是表头
  getBatch?: Function
  getReadonly?: Function
  getProxyStatus?: Function
  getCurrentType?: Function
  getDefaultValue?: Function
  handleValueChange?: Function
  handleBlur?: Function
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

export type ISafetyType = 'RSA'|'SM2';

export interface ISafetyOption {
  name?: string
  type?: ISafetyType;
  publicKey?: string;
  privateKey?: string;
}

export interface IKeyItem {
  name: string
  description: string
  cipher_type: ISafetyType
  content: string
}
