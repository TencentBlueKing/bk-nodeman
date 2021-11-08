import { MainStore } from '@/store';
import { RSA } from '@/setup/encrypt';
import { RouteConfig } from 'vue-router';
import { AGENT_VIEW, AGENT_OPERATE } from '../action-map';
const AgentStatus = () => import(/* webpackChunkName: 'AgentStatus' */'@/views/agent/agent-list.vue');
const AgentSetup = () => import(/* webpackChunkName: 'AgentSetup' */'@/views/agent/agent-setup/agent-setup.vue');
const AgentImport = () => import(/* webpackChunkName: 'AgentImport' */'@/views/agent/agent-setup/agent-import.vue');

export default [
  {
    path: '/agent-manager/status',
    name: 'agentStatus',
    props: true,
    component: AgentStatus,
    meta: {
      navId: 'agentManager',
      title: 'Agent管理',
      authority: {
        page: AGENT_VIEW,
        operate: AGENT_OPERATE,
      },
    },
  },
  {
    path: '/agent-manager/setup',
    name: 'agentSetup',
    component: AgentSetup,
    meta: {
      navId: 'agentManager',
      title: '普通安装',
      authority: {
        page: AGENT_OPERATE,
      },
    },
    beforeEnter: (to: Route, from: Route, next: () => void) => {
      beforeEnter();
      next();
    },
  },
  {
    path: '/agent-manager/import',
    name: 'agentImport',
    props: true,
    component: AgentImport,
    meta: {
      navId: 'agentManager',
      title: 'Excel导入安装',
      authority: {
        page: AGENT_OPERATE,
      },
    },
    beforeEnter: (to: Route, from: Route, next: () => void) => {
      beforeEnter();
      next();
    },
  },
  {
    path: '/agent-manager/edit',
    name: 'agentEdit',
    props: true,
    component: AgentImport,
    meta: {
      navId: 'agentManager',
      needBack: true,
      authority: {
        page: AGENT_OPERATE,
      },
    },
    beforeEnter: (to: Route, from: Route, next: () => void) => {
      beforeEnter();
      next();
    },
  },
] as RouteConfig[];

function beforeEnter() {
  MainStore.getPublicKeyRSA().then(publicKey => RSA.setPublicKey(publicKey));
}
