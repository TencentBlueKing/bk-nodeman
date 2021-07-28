import './public-path';
import Vue from 'vue';

import App from '@/App.vue';
import router from '@/router';
import store from '@/store/index';
import { bus } from '@/common/bus';
import i18n from '@/setup';
import LoadingIcon from '@/components/common/loading-icon.vue';
import { formatTimeByTimezone } from './common/util';
import '@icon-cool/bk-icon-node-manager';

if (process.env.NODE_ENV === 'development') {
  Vue.config.devtools = true;
}

Vue.component('LoadingIcon', LoadingIcon);
Vue.prototype.formatTimeByTimezone = formatTimeByTimezone;

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
