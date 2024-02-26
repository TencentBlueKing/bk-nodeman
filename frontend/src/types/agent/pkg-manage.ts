import { TranslateResult } from 'vue-i18n';

// import { TranslateResult } from 'vue-i18n'
export type PkgType = 'gse_agent' | 'gse_proxy';
export type PkgTagType = 'builtin' | 'custom';

// tag相关的参数 都是使用原本的name字段, 原本的description用于展示
export interface IPkgTag {
  id?: number;
  name:  string;
  description: string;
  // 附加的
  className?: string
}
export interface IPkgTagOpt extends IPkgTag {
  id: string;
  description?: string;
};

export interface IPkgTagList {
  name: PkgTagType;
  description: string;
  children: IPkgTag[];
}

export interface IPkgParams {
  project: PkgType;
  page: number;
  pagesize: number;
  tags?: string; // ,分隔
  os?: string; // 操作系统
  cpu_arch?: string; // 架构
  created_by?: string; // ,分隔
  is_ready?: string; // true,false
  version?: string; // ,分隔
  created_time_before?: string; // 2022-10-01T00:00:00
  created_time_after?: string;
}

export interface IPkgQuickOpt {
  id: string;
  name: string | TranslateResult;
  count: number;
  icon?: string;
  tips?: boolean;
  isAll?: boolean;
}

export interface IPkgDimension {
  id: string;
  name: string;
  children: IPkgQuickOpt[]
}


export interface IPkgInfo {
  id: number;
  pkg_name: string; // 包名称
  version: string; // 版本号
  os: string; // 操作系统
  cpu_arch: string; // 架构
  created_by: string; // 上传用户
  created_time: string; // 上传时间
  is_ready: boolean; // 状态
  tags: IPkgTagList[];
}

export interface IPkgRow extends IPkgInfo {
  hostNumber: string | number;
  formatTags: IPkgTag[];
}

export interface IPkgDelpyNumber {
  count?: number;
  cpu_arch: string;
  os_type: string;
  version: string;
}

export interface IPkgParseInfo {
  project: PkgType;
  os: string;
  cpu_arch: string;
  pkg_name: string;
  version: string;
  config_templates: any[];
}

export interface IPkgVersion {
  project: PkgType;
  version: string;
  packages: {
    pkg_name: string;
    tags: IPkgTag[];
  }[];
  tags: IPkgTag[];
  description: string;
}
