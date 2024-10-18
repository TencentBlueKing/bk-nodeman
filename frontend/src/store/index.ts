import { getModule } from 'vuex-module-decorators';
import Vue from 'vue';
import Vuex from 'vuex';
import { unifyObjectStyle } from '@/common/util';
import main from '@/store/modules/main';
import agent from '@/store/modules/agent';
import cloud from '@/store/modules/cloud';
import pluginNew from '@/store/modules/plugin-new';
import pluginOld from '@/store/modules/plugin';
import task from '@/store/modules/task';
import config from '@/store/modules/config';
import platformConfig from '@/store/modules/platform-config';


Vue.use(Vuex);
Vue.config.devtools = process.env.NODE_ENV === 'development';

const store = new Vuex.Store({
  // 与modules里的命名需保持一致
  modules: {
    agent,
    cloud,
    pluginNew,
    pluginOld,
    task,
    config,
    main,
    platformConfig,
  },
});

/**
 * hack vuex dispatch, add third parameter `config` to the dispatch method
 *
 * @param {Object|string} _type vuex type
 * @param {Object} _payload vuex payload
 * @param {Object} config config 参数，主要指 http 的参数，详见 src/api/index initConfig
 *
 * @return {Promise} 执行请求的 promise
 */
store.dispatch = function (_type: string, _payload: any, config = {}) {
  const { type, payload } = unifyObjectStyle(_type, _payload, null);

  const action = { type, payload, config };
  const entry = store._actions[type];
  if (!entry) {
    if (NODE_ENV !== 'production') {
      console.error(`[vuex] unknown action type: ${type}`);
    }
    return;
  }

  store._actionSubscribers.forEach((sub: Function) => {
    if (typeof sub === 'function') {
      sub(action, store.state);
    } else if (sub.after && typeof sub.after === 'function') {
      sub.after && sub.after(action, store.state);
    }
  });

  return entry.length > 1
    ? Promise.all(entry.map((handler: Function) => handler(payload, config)))
    : entry[0](payload, config);
};

const MainStore = getModule(main, store);
const AgentStore = getModule(agent, store);
const CloudStore = getModule(cloud, store);
const PluginStore = getModule(pluginNew, store);
const PluginOldStore = getModule(pluginOld, store);
const TaskStore = getModule(task, store);
const ConfigStore = getModule(config, store);
const PlatformConfigStore = getModule(platformConfig, store);

export {
  MainStore,
  AgentStore,
  CloudStore,
  PluginStore,
  PluginOldStore,
  TaskStore,
  ConfigStore,
  PlatformConfigStore,
};

export default store;
