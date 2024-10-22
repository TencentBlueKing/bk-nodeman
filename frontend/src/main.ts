import './public-path';
import Vue from 'vue';

import App from '@/App.vue';
import i18n from '@/setup';
import router from '@/router';
import store from '@/store/index';
import { bus } from '@/common/bus';
import LoadingIcon from '@/components/common/loading-icon.vue';
import NmException from '@/components/common/nm-exception.vue';
// import '@icon-cool/bk-icon-node-manager';
import '@/bk_icon_font/style.css';
import 'github-markdown-css';
import { subEnv } from '@blueking/sub-saas';
import IframeApp from './IframeApp.vue';

if (process.env.NODE_ENV === 'development') {
  Vue.config.devtools = true;
}

Vue.component('LoadingIcon', LoadingIcon);
Vue.component('NmException', NmException);
Vue.prototype.$DHCP = window.$DHCP;

global.bus = bus;
global.mainComponent = new Vue({
  el: '#app',
  router,
  store,
  i18n,
  components: { App: subEnv ? IframeApp : App },
  template: '<App/>',
});
