import { INavConfig } from '@/types/index';
export const navConfig: INavConfig[] = [
  {
    title: '节点管理',
    name: 'nodeManage',
    currentActive: 'agentStatus',
    defaultActive: 'agentStatus',
    children: [
      {
        name: 'Agent状态',
        children: [
          {
            title: 'Agent状态',
            icon: 'nc-state',
            path: '/agent-manager/status',
            name: 'agentStatus',
          },
          // {
          //   title: '普通安装',
          //   icon: 'nc-install',
          //   path: '/agent-manager/setup',
          //   name: 'agentSetup',
          // },
          // {
          //   title: 'Excel导入安装',
          //   icon: 'nc-icon-excel-fill',
          //   path: '/agent-manager/import',
          //   name: 'agentImport',
          // },
        ],
      },
      {
        name: '插件管理',
        children: [
          {
            title: '插件状态',
            icon: 'nc-plug-in',
            path: '/plugin-new/list', // '/plugin-manager/list',
            name: 'plugin',
          },
          {
            title: '插件部署',
            icon: 'nc-strategy',
            path: '/plugin-manager/rule',
            name: 'pluginRule',
          },
          {
            title: 'IP选择器',
            icon: 'nc-strategy',
            path: '/plugin-manager/ip-selector',
            name: 'ipSelector',
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
        name: '历史',
        children: [
          {
            title: '任务历史',
            icon: 'nc-history',
            path: '/task-list',
            name: 'taskList',
          },
        ],
      },
    ],
  },
  {
    title: '云区域管理',
    path: '/cloud-manager',
    name: 'cloudManager',
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
