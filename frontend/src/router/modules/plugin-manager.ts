/* eslint-disable max-len */
import { RouteConfig, Route } from 'vue-router';
import { MainStore } from '@/store/index';
import { STRATEGY_VIEW, STRATEGY_CREATE, PLUGIN_VIEW } from '../action-map';
import { IRuleRouterParams, pluginOperate, grayRuleType, stepOperate } from '@/views/plugin/operateConfig';

const Plugin = () => import(/* webpackChunkName: 'Plugin' */'@/views/plugin/plugin-list/plugin-list.vue');
const pluginRule = () => import(/* webpackChunkName: 'PluginRule' */'@/views/plugin/plugin-rule/plugin-rule.vue');
const PluginPackage = () => import(/* webpackChunkName: 'PluginPackage' */'@/views/plugin/plugin-package/index.vue');
const PackageParse = () => import(/* webpackChunkName: 'PackageParse' */'@/views/plugin/plugin-package/plugin-package-parsing.vue');
const PluginDetail = () => import(/* webpackChunkName: 'PluginDetail' */'@/views/plugin/plugin-package/plugin-detail.vue');
const ChooseRule = () => import(/* webpackChunkName: 'AddRule' */'@/views/plugin/plugin-rule/plugin-rule-choose/plugin-rule-choose.vue');
const CreateRule = () => import(/* webpackChunkName: 'CreateRule' */'@/views/plugin/plugin-rule/plugin-rule-create/index.vue');
const ResourceQuota = () => import(/* webpackChunkName: 'ResourceQuota' */'@/views/plugin/resource-quota/index.vue');
const ResourceQuotaEdit = () => import(/* webpackChunkName: 'ResourceQuotaEdit' */'@/views/plugin/resource-quota/edit.vue');

export default [
  // 其它saas跳转
  {
    path: '/plugin-manager',
    name: 'pluginManager',
    redirect: { name: 'plugin' },
  },
  {
    path: '/plugin-manager/list',
    name: 'pluginManager',
    redirect: { name: 'plugin' },
  },
  {
    path: '/plugin-new/list', // path: 'plugin-manager/list',
    name: 'plugin',
    component: Plugin,
    props: route => ({ // 兼容旧的路由
      ip: route.query.ip, // 主机ip
      cloudId: route.query.cloud_id,
      osType: route.query.os_type,
      pluginName: route.query.name, // 插件名称
      // 其它不支持
      // version: route.query.version, // 更新版本
      // bkHostId: route.query.bk_host_id, // 主机ID或者IDs
      // jobType: route.query.job_type,
      // pluginType: route.query.plugin_type, // 插件类型 'official', 'scripts', 'external'
      // keepConfig: route.query.keep_config === 'true',
      // noRestart: route.query.no_restart === 'true',
    }),
    meta: {
      navId: 'pluginManagerNew',
      title: '节点列表',
      authority: {
        page: PLUGIN_VIEW,
        pk: 'plugin',
        module: 'plugin',
      },
    },
  },
  {
    path: '/plugin-new/list/:type',
    name: 'pluginOperation',
    props: true,
    component: CreateRule,
    meta: {
      navId: 'pluginManagerNew',
      title: '手动操作插件',
      customContent: true,
      parentName: 'plugin',
      needBack: true,
    },
    beforeEnter(to: Route, from: Route, next) {
      const { type, pluginId } = to.params as IRuleRouterParams;
      if (!pluginId || !pluginOperate.includes(type)) {
        next({ name: 'plugin', replace: true });
        return;
      }
      next();
    },
  },
  {
    path: '/plugin-manager/rule',
    name: 'pluginRule',
    component: pluginRule,
    meta: {
      navId: 'pluginManagerNew',
      title: '部署策略',
      authority: {
        page: STRATEGY_VIEW,
        operate: STRATEGY_CREATE,
      },
    },
  },
  {
    path: '/plugin-manager/choose-rule',
    name: 'chooseRule',
    props: true,
    component: ChooseRule,
    meta: {
      navId: 'pluginManagerNew',
      parentName: 'pluginRule',
      title: '新建部署策略',
      needBack: true,
      authority: {
        page: STRATEGY_CREATE,
      },
    },
    beforeEnter(to: Route, from: Route, next: () => void) {
      MainStore.setToggleDefaultContent(true);
      next();
    },
  },
  {
    path: '/plugin-manager/rule/:type/:id?',
    name: 'createRule',
    component: CreateRule,
    props: true,
    meta: {
      navId: 'pluginManagerNew',
      customContent: true,
      title: '新建部署策略',
      parentName: 'pluginRule',
      needBack: true,
    },
    beforeEnter(to: Route, from: Route, next) {
      const { type, pluginId, policyName, subId } = to.params as IRuleRouterParams;

      if (!pluginId && /create/ig.test(type)) {
        if (type === 'create') {
          next({ name: from.name !== 'chooseRule' ? 'chooseRule' : 'pluginRule' });
        } else {
          next({ name: 'pluginRule', replace: true });
        }
        return;
      }
      if (!subId && ['releaseGray'].includes(type)) {
        next({ name: 'pluginRule', replace: true });
        return;
      }
      if (!policyName && ['start', 'stop', 'stop_and_delete', 'deleteGray'].includes(type)) {
        next({ name: 'pluginRule', replace: true });
        return;
      }
      if (stepOperate.includes(type)) {
        MainStore.updateEdited(true);
      }

      if (pluginOperate.includes(type)) {
        to.params.ruleType = 'plugin';
      } else if (grayRuleType.includes(type)) {
        to.params.ruleType = 'gray';
      } else {
        to.params.ruleType = 'policy';
      }
      next();
    },
  },
  {
    path: '/plugin-manager/package',
    name: 'pluginPackage',
    component: PluginPackage,
    meta: {
      navId: 'pluginManagerNew',
      title: '插件包',
      authority: {
        pk: 'package',
        module: 'plugin',
      },
    },
  },
  {
    path: '/plugin-manager/package-parse/:filename',
    props: true,
    name: 'pluginPackageParse',
    component: PackageParse,
    meta: {
      navId: 'pluginManagerNew',
      parentId: 'pluginPackage',
      parentName: 'pluginPackage',
      title: '插件包解析',
      needBack: true,
      authority: {
        pk: 'package',
        module: 'plugin',
      },
    },
  },
  {
    path: '/plugin-manager/plugin-detail/:id',
    name: 'pluginDetail',
    props: true,
    component: PluginDetail,
    meta: {
      navId: 'pluginManagerNew',
      parentId: 'pluginPackage',
      parentName: 'pluginPackage',
      title: '插件详情',
      customContent: true,
      needBack: true,
    },
  },
  {
    path: '/plugin-manager/resource-quota',
    name: 'resourceQuota',
    props: route => ({
      bizId: route.query.bizId ? Number(route.query.bizId) : -1,
      moduleId: route.query.moduleId ? Number(route.query.moduleId) : -1,
    }),
    component: ResourceQuota,
    meta: {
      navId: 'pluginManagerNew',
      title: '资源配额',
      customContent: true,
    },
    async beforeEnter(to: Route, from: Route, next: () => void) {
      await MainStore.getBkBizPermission({ action: PLUGIN_VIEW, updateBiz: true });
      next();
    },
  },
  {
    path: '/plugin-manager/resource-quota/edit',
    name: 'resourceQuotaEdit',
    props: route => ({
      bizId: route.query.bizId ? Number(route.query.bizId) : -1,
      moduleId: route.query.moduleId ? Number(route.query.moduleId) : -1,
    }),
    component: ResourceQuotaEdit,
    meta: {
      navId: 'pluginManagerNew',
      parentId: 'resourceQuota',
      parentName: 'resourceQuota',
      title: '编辑资源配额',
      customContent: true,
    },
  },
] as RouteConfig[];
