import { INavConfig } from '@/types/index';
export const navConfig: INavConfig[] = [
  {
    title: 'nav_节点管理',
    name: 'nodeManage',
    currentActive: 'agentStatus',
    defaultActive: 'agentStatus',
    children: [
      {
        name: 'nav_Agent状态',
        children: [
          {
            title: 'nav_Agent状态',
            icon: 'nc-state',
            path: '/agent-manager/status',
            name: 'agentStatus',
          },
        ],
      },
      {
        name: 'nav_插件管理',
        children: [
          {
            title: 'nav_插件状态',
            icon: 'nc-plug-in',
            path: '/plugin-new/list', // '/plugin-manager/list',
            name: 'plugin',
          },
          {
            title: 'nav_插件部署',
            icon: 'nc-strategy',
            path: '/plugin-manager/rule',
            name: 'pluginRule',
          },
          {
            title: 'nav_插件包',
            icon: 'nc-package-2',
            path: '/plugin-manager/package',
            name: 'pluginPackage',
          },
          {
            title: 'nav_资源配额',
            icon: 'nc-icon-control-fill',
            path: '/plugin-manager/resource-quota',
            name: 'resourceQuota',
          },
        ],
      },
      {
        name: 'nav_历史',
        children: [
          {
            title: 'nav_任务历史',
            icon: 'nc-history',
            path: '/task-list',
            name: 'taskList',
          },
        ],
      },
    ],
  },
  {
    title: 'nav_管控区域管理',
    path: '/cloud-manager',
    name: 'cloudManager',
  },
  {
    title: 'nav_全局配置',
    name: 'globalConfig',
    currentActive: 'gseConfig',
    defaultActive: 'gseConfig',
    disabled: window.PROJECT_CONFIG.GLOBAL_SETTING_PERMISSION !== 'True',
    children: [
      {
        title: 'nav_GSE环境管理',
        icon: 'nc-environment',
        path: '/global-config/gse-config',
        name: 'gseConfig',
      },
      {
        title: 'nav_自监控',
        icon: 'nc-monitor',
        path: '/global-config/healthz',
        name: 'healthz',
      },
    ],
  },
];
export default navConfig;
