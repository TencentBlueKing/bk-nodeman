/* eslint-disable max-len */
import navList from '../navigation-config';
import { RouteConfig, Route } from 'vue-router';
import { MainStore, ConfigStore } from '@/store/index';
const GseConfig = () => import(/* webpackChunkName: 'GseConfig' */'@/views/global-config/gse-config/index.vue');
const AccessPoint = () => import(/* webpackChunkName: 'AccessPoint' */'@/views/global-config/gse-config/set-access-point/access-point.vue');
// const TaskConfig = () => import(/* webpackChunkName: 'TaskConfig' */'@/views/global-config/task-config.vue')
const Healthz = () => import(/* webpackChunkName: 'Healthz' */'@/views/global-config/healthz/index.vue');

const globalConfig = navList.find(item => item.name === 'globalConfig');

export default globalConfig && !globalConfig.disabled ? [
  {
    path: '/global-config',
    name: 'globalConfig',
    redirect: {
      name: 'GseConfig',
    },
  },
  {
    path: '/global-config/gse-config',
    name: 'gseConfig',
    component: GseConfig,
    meta: {
      navId: 'globalConfig',
      title: 'nav_GSE环境管理',
    },
  },
  {
    path: '/global-config/access-point/:pointId?',
    name: 'accessPoint',
    props: true,
    component: AccessPoint,
    meta: {
      navId: 'globalConfig',
      needBack: true,
    },
    beforeEnter: (to: Route, from: Route, next: () => void) => {
      ConfigStore.resetDetail();
      MainStore.setNavTitle(!to.params.pointId ? 'nav_新增接入点' : 'nav_编辑接入点');
      MainStore.setToggleDefaultContent(true);
      next();
    },
  },
  // {
  //   path: 'global-config/task-config',
  //   name: 'taskConfig',
  //   component: TaskConfig,
  //   meta: {
  //     navId: 'globalConfig',
  //     title: '任务配置'
  //   }
  {
    path: '/global-config/healthz',
    name: 'healthz',
    component: Healthz,
    meta: {
      navId: 'globalConfig',
      title: 'nav_自监控',
    },
  },
] as RouteConfig[] : [];
