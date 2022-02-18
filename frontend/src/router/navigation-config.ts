import { INavConfig } from '@/types/index';
const navConfig: INavConfig[] = [
  {
    title: 'Agent管理',
    name: 'agentManager',
    currentActive: 'agentStatus',
    defaultActive: 'agentStatus',
    children: [
      {
        title: 'Agent状态',
        icon: 'nc-state',
        path: '/agent-manager/status',
        name: 'agentStatus',
        group: true,
      },
      {
        title: '普通安装',
        icon: 'nc-install',
        path: '/agent-manager/setup',
        name: 'agentSetup',
      },
      {
        title: 'Excel导入安装',
        icon: 'nc-icon-excel-fill',
        path: '/agent-manager/import',
        name: 'agentImport',
      },
    ],
  },
  // {
  //   title: '插件管理',
  //   path: '/plugin-manager',
  //   name: 'pluginManager'
  // },
  {
    title: '插件管理',
    name: 'pluginManagerNew',
    currentActive: 'plugin',
    defaultActive: 'plugin',
    disabled: false,
    children: [
      {
        title: '节点列表',
        icon: 'nc-state',
        path: '/plugin-new/list', // '/plugin-manager/list',
        name: 'plugin',
      },
      {
        title: '部署策略',
        icon: 'nc-strategy',
        path: '/plugin-manager/rule',
        name: 'pluginRule',
      },
      {
        title: '插件包',
        icon: 'nc-package-2',
        path: '/plugin-manager/package',
        name: 'pluginPackage',
      },
      {
        title: '资源配额',
        icon: 'nc-icon-control-fill',
        path: '/plugin-manager/resource-quota',
        name: 'resourceQuota',
      },
    ],
  },
  {
    title: '云区域管理',
    path: '/cloud-manager',
    name: 'cloudManager',
  },
  // {
  //   title: '任务历史',
  //   path: '/task-history',
  //   name: 'taskHistory'
  // },
  {
    title: '任务历史',
    path: '/task-list',
    name: 'taskList',
  },
  {
    title: '全局配置',
    name: 'globalConfig',
    currentActive: 'gseConfig',
    defaultActive: 'gseConfig',
    disabled: window.PROJECT_CONFIG.GLOBAL_SETTING_PERMISSION !== 'True',
    children: [
      {
        title: 'GSE环境管理',
        icon: 'nc-environment',
        path: '/global-config/gse-config',
        name: 'gseConfig',
      // },
      // {
      //   title: '任务配置',
      //   icon: 'nc-icon-control-fill',
      //   path: '/global-config/task-config',
      //   name: 'taskConfig'
      },
      {
        title: '自监控',
        icon: 'nc-monitor',
        path: '/global-config/healthz',
        name: 'healthz',
      },
    ],
  },
];
export default navConfig;
