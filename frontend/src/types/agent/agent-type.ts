
/* eslint-disable camelcase */

import { TranslateResult } from 'vue-i18n';

// import { TranslateResult } from 'vue-i18n'
export interface IAgent {
  [prop: string]: any
}

export interface IAgentHost {
  bk_host_id: number
  os_type: string
  port: number
  inner_ip: string
  data_ip: string
  login_ip: string
  outer_ip: string
  status: string
  version: string
  ap_id: number
  bk_biz_id: number
  bk_biz_name: string
  bk_cloud_id: number
  bk_cloud_name: string
  is_manual: boolean
  bt_speed_limit: string
  peer_exchange_switch_for_agent: boolean
  topology: string[]
  status_display: string
  selection: boolean
  operate_permission: boolean
  created_at: string
  updated_at: string
  extra_data: {
    bt_speed_limit?: string
    peer_exchange_switch_for_agent: number
  }
  identity_info: {
    account: string
    auth_type: string
    port: number
    re_certification: boolean
  }
  job_result: {
    current_step: string
    instance_id: string
    job_id: number
    status: string
  }
  install_channel_id: number | string | null
}

export interface IPagination {
  current: number
  count: number
  limit: number
  limitList?: number[]
}

export interface IAgentSearch {
  page?: number,
  pagesize?: number,
  extra_data?: string[]
  bk_biz_id?: number
  sort?: { head: string, sort_type: 'ASC' | 'DEC' }
  conditions?: { key: string, value: any }[],
  bk_host_id?: number[]
}

export interface IAgentSearchIp extends IAgentSearch {
  only_ip: boolean
  exclude_hosts?: Array<number>
}

export interface IAgentJob {
  job_type: string
  only_ip?: boolean
  is_proxy?: boolean
  hosts?: IAgentHost[]
  exclude_hosts?: IAgentHost[]
}

export interface IOperateItem {
  id: string
  name: string | TranslateResult
  disabled?: boolean
  show?: boolean
  single?: boolean
  tips?: string | TranslateResult
}

export interface IAgentTable {
  runningCount: number
  noPermissionCount: number
  data: IAgentHost[]
  pagination: IPagination
}

export interface IAgentTopo {
  name: string
  id: number
  type?: string
  children?: IAgentTopo[]
  disabled: boolean
  isLoading?: boolean
  needLoad?: boolean
}

export interface IFilterDialogRow {
  ip: string
  msg: string
}
