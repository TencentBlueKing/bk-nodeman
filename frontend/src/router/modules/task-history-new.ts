import { MainStore, TaskStore } from '@/store/index';
import { Route } from 'vue-router';
import { TASK_HISTORY_VIEW } from '@/router/action-map';
const TaskList = () => import(/* webpackChunkName: 'TaskList' */'@/views/task/task-list.vue');
const TaskDetail = () => import(/* webpackChunkName: 'TaskDetail' */'@/views/task/task-detail-new.vue');
const TaskLog = () => import(/* webpackChunkName: 'TaskLog' */'@/views/task/task-log.vue');

export default [
  // 其它saas跳转 - 兼容旧的路由
  {
    path: '/task-history',
    name: 'taskHistory',
    redirect: { name: 'taskList' },
  },
  {
    path: '/task-history/detail/:taskId',
    redirect: { name: 'taskDetail' },
  },
  {
    path: '/task-history/:taskId/log/:instanceId',
    redirect: { name: 'taskLog' },
  },

  {
    path: '/task-list',
    name: 'taskList',
    component: TaskList,
    meta: {
      navId: 'nodeManage',
      title: 'nav_任务历史',
      customContent: true,
      authority: {
        page: TASK_HISTORY_VIEW,
      },
    },
  },
  {
    path: '/task-list/detail/:taskId',
    name: 'taskDetail',
    props: true,
    component: TaskDetail,
    meta: {
      parentName: 'taskList',
      navId: 'nodeManage',
      title: 'nav_任务详情',
      needBack: true,
      customContent: true,
      authority: {
        page: TASK_HISTORY_VIEW,
      },
    },
    beforeEnter: (to: Route, from: Route, next: () => void) => {
      TaskStore.setRouterParent(from.name || '');
      MainStore.setToggleDefaultContent(true);
      next();
    },
  },
  {
    path: '/task-list/:taskId/log/:instanceId',
    name: 'taskLog',
    props: (route: Route) => ({
      ...route.params,
      query: route.query,
    }),
    component: TaskLog,
    meta: {
      parentName: 'taskList',
      navId: 'nodeManage',
      title: 'nav_执行日志',
      needBack: true,
      customContent: true,
      authority: {
        page: TASK_HISTORY_VIEW,
      },
    },
    beforeEnter: (to: Route, from: Route, next: () => void) => {
      TaskStore.setRouterParent(from.name || '');
      next();
    },
  },
];
