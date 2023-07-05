import { RouteConfig } from 'vue-router';
import { PLUGIN_VIEW } from '@/router/action-map';
const PluginOld = () => import(/* webpackChunkName: 'PluginOld' */'@/views/plugin/plugin-old/index.vue');
export default [
  {
    path: '/plugin-manager',
    name: 'pluginManager',
    redirect: {
      name: 'plugin',
    },
  },
  /**
   * 1.3版本组件
   */
  {
    path: '/plugin-manager/list',
    name: 'pluginOld',
    redirect: {
      name: 'plugin',
    },
    props: route => ({
      ip: route.query.ip,
      cloudId: route.query.cloud_id,
      osType: route.query.os_type,
      name: route.query.name,
      bkHostId: route.query.bk_host_id,
      keepConfig: route.query.keep_config === 'true',
      noRestart: route.query.no_restart === 'true',
      version: route.query.version,
      jobType: route.query.job_type,
      pluginType: route.query.plugin_type,
    }),
    component: PluginOld,
    meta: {
      navId: 'pluginManager',
      title: 'nav_插件管理',
      customContent: true,
      authority: {
        page: PLUGIN_VIEW,
      },
    },
  },
] as RouteConfig[];
