/* eslint-disable max-len */
import { RouteConfig } from 'vue-router';
import { PROXY_OPERATE, CLOUD_VIEW } from '@/router/action-map';
const CloudManager = () => import(/* webpackChunkName: 'CloudManager' */'@/views/cloud/cloud-manager.vue');
const AddCloudManager = () => import(/* webpackChunkName: 'AddCloudManager' */'@/views/cloud/cloud-manager-add/cloud-manager-add.vue');
const AddCloudManagerPreview = () => import(/* webpackChunkName: 'AddCloudManagerPreview' */'@/views/cloud/cloud-manager-add/cloud-manager-preview.vue');
const SetupCloudManager = () => import(/* webpackChunkName: 'SetupCloudManager' */'@/views/cloud/cloud-manager-add/cloud-manager-setup.vue');
const CloudManagerDetail = () => import(/* webpackChunkName: 'CloudManagerDetail' */'@/views/cloud/cloud-manager-detail/cloud-manager-detail.vue');

export default [
  {
    path: '/cloud-manager',
    name: 'cloudManager',
    component: CloudManager,
    meta: {
      navId: 'cloudManager',
      title: '云区域管理',
    },
  },
  {
    path: '/cloud-manager/form/:type/:id?',
    props: true,
    name: 'addCloudManager',
    component: AddCloudManager,
    meta: {
      navId: 'cloudManager',
      title: '新建云区域',
      needBack: true,
    },
  },
  {
    path: '/cloud-manager/form/:type/:id/preview',
    props: true,
    name: 'addManagerPreview',
    component: AddCloudManagerPreview,
    meta: {
      navId: 'cloudManager',
      title: '重装Proxy',
      needBack: true,
    },
    beforeEnter(to: Route, from: Route, next) {
      const { formData } = to.params as IRuleRouterParams;
      if (formData) {
        next();
      } else {
        next({ name: 'cloudManager' });
      }
    },
  },
  {
    path: '/cloud-manager/setup/:type/:id?',
    props: true,
    name: 'setupCloudManager',
    component: SetupCloudManager,
    meta: {
      navId: 'cloudManager',
      title: '安装Proxy',
      needBack: true,
      authority: {
        page: PROXY_OPERATE,
      },
    },
  },
  {
    path: '/cloud-manager/detail/:id?',
    name: 'cloudManagerDetail',
    props: true,
    component: CloudManagerDetail,
    meta: {
      navId: 'cloudManager',
      title: '云区域详情',
      customContent: true,
      needBack: true,
      authority: {
        page: CLOUD_VIEW,
      },
    },
  },
] as RouteConfig[];
