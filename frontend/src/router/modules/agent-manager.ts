import { RouteConfig } from 'vue-router';
import { AGENT_VIEW, AGENT_OPERATE } from '../action-map';
const AgentStatus = () => import(/* webpackChunkName: 'AgentStatus' */'@/views/agent/agent-list.vue');
const AgentSetup = () => import(/* webpackChunkName: 'AgentSetup' */'@/views/agent/agent-setup/agent-setup.vue');
const AgentImport = () => import(/* webpackChunkName: 'AgentImport' */'@/views/agent/agent-setup/agent-import.vue');

export default [
  {
    path: '/agent-manager/status',
    name: 'agentStatus',
    props: (router) => {
      const props: any = {};
      Object.keys(router.query).forEach((key) => {
        let value = router.query[key].replace(/[\s;,]+/ig, ' ').split(/\s+/g);
        if (key === 'bizId') {
          value = value.map(item => parseInt(item, 10));
        }
        props[key] = value;
      });
      return props;
    },
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
  },
] as RouteConfig[];
