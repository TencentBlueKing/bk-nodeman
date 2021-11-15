import Vue from 'vue';
import VueRouter, { RouteConfig, Route } from 'vue-router';

import { MainStore, CloudStore, PluginStore } from '@/store/index';
import http from '@/api';
import { PROXY_OPERATE, CLOUD_VIEW, CLOUD_CREATE, CLOUD_EDIT } from '@/router/action-map';
import axios from 'axios';

Vue.use(VueRouter);
// 获取modules下的所有模块
const routeFiles = require.context('./modules', true, /\.ts$/);
const pageRoute = routeFiles.keys().reduce<RouteConfig[]>((route, modulePath) => {
  const value = routeFiles(modulePath);
  route.push(value.default);
  return route;
}, []);

const MainEntry = () => import(/* webpackChunkName: 'entry' */'@/views/index.vue');
const NotFound = () => import(/* webpackChunkName: 'none' */'@/views/404.vue');

const routes = [
  {
    path: '/',
    component: MainEntry,
    children: [
      {
        path: '',
        redirect: {
          name: 'agentStatus',
        },
      },
    ],
  },
  ...pageRoute.flat(),
  // 404
  {
    path: '*',
    name: '404',
    component: NotFound,
  },
];

const router = new VueRouter({
  mode: 'hash',
  routes,
});

const loadOsRoute = ['agentSetup', 'agentImport', 'agentEdit'];
const cancelRequest = async () => {
  const allRequest = http.queue.get() as any[];
  const requestQueue = allRequest.filter(request => request.cancelWhenRouteChange);
  await http.cancel(requestQueue.map(request => request.requestId));
};
const beforeRouterMethod = async (to: Route, next: any) => {
  const { title, navId, authority, customContent } = to.meta;
  // 重置表单编辑态
  MainStore.updateEdited(false);
  // 设置默认背景色
  MainStore.setToggleDefaultContent(false);
  // 设置自定义导航内容
  // MainStore.setCustomNavContent(customContent)
  // 设置标题
  if (!customContent) {
    MainStore.setNavTitle(to.params.title || window.i18n.t(title));
  }
  // 更新当前导航name
  MainStore.updateCurrentNavName(navId);
  // 更新子导航name
  MainStore.updateSubMenuName({
    name: to.name || '',
    parentName: to.meta.parentName,
  });
  // 重置业务权限
  MainStore.updateBizAction(authority ? authority.page : '');
  await cancelRequest();
  if (!MainStore.osList) {
    if (loadOsRoute.includes(to.name)) {
      const list = await MainStore.getOsList();
      MainStore.updateOsList(list);
    } else {
      MainStore.getOsList().then(list => MainStore.updateOsList(list));
    }
  }
  next();
};

router.beforeEach(async (to, from, next) => {
  if (MainStore.edited) {
    global.mainComponent.$bkInfo({
      title: window.i18n.t('确定离开当前页'),
      subTitle: window.i18n.t('离开将会导致未保存的信息丢失'),
      confirmFn: async () => {
        await beforeRouterMethod(to, next);
      },
      cancelFn: () => {
        // 还原导航
        MainStore.updateSubMenuName({
          name: from.name || '',
          parentName: from.meta.parentName,
        });
        next(false);
      },
    });
  } else {
    beforeRouterMethod(to, next);
  }
});

// 校验普通界面权限
const validateBizAuth = async (to: Route) => {
  const { authority } = to.meta;
  if (window.PROJECT_CONFIG.USE_IAM === 'True' && authority) {
    if (authority.page) {
      MainStore.setNmMainLoading(true);
      const list = await MainStore.getBkBizPermission({ action: authority.page, updateBiz: true });
      // 设置当前路由的界面权限
      MainStore.updatePagePermission(!axios.isCancel(list) ? !!list.length : true);
    }
    if (authority.pk && authority.module) {
      MainStore.setNmMainLoading(true);
      let store: any = null;
      const list = await MainStore.getPagePermission(authority.pk);
      switch (authority.module) {
        // case 'cloud':
        //   store = CloudStore
        case 'plugin':
          store = PluginStore;
      }
      store.updateAuthority && store.updateAuthority({
        ...list,
      });
    }
  }
  MainStore.setNmMainLoading(false);
};
// 校验云区域界面
const validateCloudAuth = async (to: Route) => {
  const { authority } = to.meta;
  // const authorityMap = store.getters['cloud/authority']
  const permissionSwitch = window.PROJECT_CONFIG.USE_IAM === 'True';
  if (permissionSwitch) {
    // 获取权限
    const promiseList = [
      CloudStore.getCloudPermission(),
      MainStore.getBkBizPermission({ action: 'proxy_operate', updateBiz: true }),
    ];
    const [cloudAction, proxyOperateList] = await Promise.all(promiseList);
    if (!axios.isCancel(cloudAction) && !axios.isCancel(proxyOperateList)) {
      CloudStore.setAuthority({
        ...cloudAction,
        proxy_operate: proxyOperateList,
      });
    }
    // 设置界面显示
    let isAuth = true;
    if (to?.name === 'addCloudManager' && !axios.isCancel(cloudAction)) {
      const { edit_action: editAction, create_action: createAction } = cloudAction;
      if (to.params?.type === 'edit') {
        MainStore.updateBizAction(CLOUD_EDIT);
        isAuth = editAction?.includes(Number(to.params.id));
      } else {
        MainStore.updateBizAction(CLOUD_CREATE);
        isAuth = !!createAction;
      }
    } else if (authority?.page === PROXY_OPERATE && !axios.isCancel(proxyOperateList)) {
      isAuth = !!proxyOperateList.length;
    } else if (authority?.page === CLOUD_VIEW && !axios.isCancel(cloudAction)) {
      const { view_action: viewAction } = cloudAction;
      isAuth = viewAction?.includes(Number(to.params.id));
    }
    // 设置当前路由的界面权限
    MainStore.updatePagePermission(isAuth);
  } else {
    // 设置默认值
    CloudStore.setAuthority({
      edit_action: [],
      delete_action: [],
      create_action: true,
      view_action: [],
      proxy_operate: [],
    });
  }
};
router.afterEach(async (to) => {
  // 设置自定义导航内容
  MainStore.setCustomNavContent(to.meta.customContent);
  // 重置界面权限
  MainStore.updatePagePermission(true);
  MainStore.updateScreenInfo(window.innerHeight);
  const { navId } = to.meta;
  if (navId === 'cloudManager') {
    await validateCloudAuth(to);
  } else {
    await validateBizAuth(to);
  }
});

export default router;
