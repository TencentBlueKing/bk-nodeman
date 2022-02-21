import './public-path';
import Vue from 'vue';

import App from '@/App.vue';
import router from '@/router';
import store from '@/store/index';
import { bus } from '@/common/bus';
import i18n from '@/setup';
import LoadingIcon from '@/components/common/loading-icon.vue';
import '@icon-cool/bk-icon-node-manager';
import 'github-markdown-css';

if (process.env.NODE_ENV === 'development') {
  Vue.config.devtools = true;
}

Vue.component('LoadingIcon', LoadingIcon);

global.bus = bus;
global.i18n = i18n;
global.mainComponent = new Vue({
  el: '#app',
  router,
  store,
  i18n,
  components: { App },
  template: '<App/>',
});
