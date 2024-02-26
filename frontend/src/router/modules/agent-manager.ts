import { RouteConfig } from 'vue-router';
import { AGENT_VIEW, AGENT_OPERATE } from '../action-map';
const AgentStatus = () => import(/* webpackChunkName: 'AgentStatus' */'@/views/agent/agent-list.vue');
const AgentSetup = () => import(/* webpackChunkName: 'AgentSetup' */'@/views/agent/agent-setup/agent-setup.vue');
const AgentImport = () => import(/* webpackChunkName: 'AgentImport' */'@/views/agent/agent-setup/agent-import.vue');
const AgentPackage = () => import(/* webpackChunkName: 'AgentPackage' */'@/views/agent/package/index.vue');

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
      navId: 'nodeManage',
      title: 'nav_Agent状态',
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
      parentName: 'agentStatus',
      navId: 'nodeManage',
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
      parentName: 'agentStatus',
      navId: 'nodeManage',
      title: 'nav_Excel导入安装',
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
      parentName: 'agentStatus',
      navId: 'nodeManage',
      needBack: true,
      authority: {
        page: AGENT_OPERATE,
      },
    },
  },
  {
    path: '/agent-manager/package',
    name: 'agentPackage',
    component: AgentPackage,
    meta: {
      navId: 'nodeManage',
      title: 'nav_Agent包管理',
      customContent: true,
      authority: {
        page: AGENT_VIEW,
        operate: AGENT_OPERATE,
      },
    },
  },
] as RouteConfig[];
