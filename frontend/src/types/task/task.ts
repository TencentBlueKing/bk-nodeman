import { TranslateResult } from 'vue-i18n';
import { ICondition } from '../index';

/* eslint-disable camelcase */
export type TaskType = 'agent' | 'proxy' | 'plugin';

export interface IParams {
  id?: string
  jobId?: string
  params?: any
}

export interface IFilter {
  name: string
  id: string
  checked?: boolean
  multiable?: boolean
  children?: IFilter[]
  values?: IFilter[]
}

export interface IRow {
  id: number| string
  bkBizScopeDisplay: string[]
  jobTypeDisplay: string
  createdBy: string
  startTime: string
  costTime: string
  status: string
  totalCount: string
  successCount: string
  failedCount: string
}

export interface ITaskInfo {
  id: string
  alias: string
  deployType: string
  sourceAppName: string
  link?: string
  description: string
  developers: string
}

export interface ITaskInfoConfig {
  prop: keyof ITaskInfo
  label: string | TranslateResult
  editable?: boolean
  isLink?: boolean
}

export interface ISort {
  head: string
  sort_type: string
}

export interface ITaskParams {
  page?: number
  pagesize: number
  bk_biz_id?: number | number[]
  sort?: ISort
  category?: TaskType
  job_id?: number[]
  conditions?: ICondition[]
  instance_id?: string
  instance_id_list?: string[]
  cloud_id_ip?: {
    [key: 'ipv6'|'ipv4']: boolean;
  }
}

export interface ITotalCount {
  failedCount: number
  filterCount?: number
  ignoredCount?: number
  pendingCount: number
  runningCount: number
  successCount: number
  totalCount: number
}

export interface IHistory extends ITotalCount {
  id: number
  jobType: string
  jobTypeDisplay: string
  bkBizScope: number[]
  bkBizScopeDisplay: string[]
  costTime: string
  createdBy: string
  startTime: string
  status: string
  subscriptionId: number
  statistics: ITotalCount
  taskIdList: number[]
}

export interface ITask {
  ipFilterList: string[]
  jobType: string
  jobTypeDisplay: string
  list: ITaskHost[]
  startTime: string
  endTime: string
  costTime: string
  statistics: ITotalCount
  status: string
  total: number
  meta: Dictionary
  pluginName: string
  createdBy: string
  jobId?: number
}

export interface ITaskHost {
  apId: number
  bkBizId: number
  bkBizName: string
  bkCloudId: number
  bkCloudName: string
  bk_cloud_id?: number
  bk_cloud_name?: string
  bkHostId: number
  ip: string
  innerIp: string
  innerIpv6: string
  instanceId: string
  isManual: false
  nodeId?: number
  status: string
  statusDisplay: string
  loading?: boolean
  jobId?: number
  exception?: string
  step?: string // 判断是否需要展示手动命令查看按钮
  opType?: string
  opTypeDisplay?: string
  suppressedById?: number
}

export interface ITaskSolutions {
  type: string
  description: string
  steps: {
    type: 'commands' | 'dependencies'
    description: string
    contents: ITaskSolutionsCommand[] | ITaskSolutionsFile[]
  }[]
}
export interface ITaskSolutionsCommand {
  type?: 'commands'
  name: string
  text: string
  show_description: boolean
  description: string
}
export interface ITaskSolutionsFile {
  name: string
  text: string
  description: string
}
